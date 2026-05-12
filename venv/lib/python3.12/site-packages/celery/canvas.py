"""Composing task work-flows.

.. seealso:

    You should import these from :mod:`celery` and not this module.
"""

import itertools
import operator
from collections import deque
from collections.abc import MutableSequence
from copy import deepcopy
from functools import partial as _partial
from functools import reduce
from operator import itemgetter
from types import GeneratorType

from kombu.utils.functional import fxrange, reprcall
from kombu.utils.objects import cached_property
from kombu.utils.uuid import uuid
from vine import barrier

from celery._state import current_app
from celery.result import GroupResult, allow_join_result
from celery.utils import abstract
from celery.utils.collections import ChainMap
from celery.utils.functional import _regen
from celery.utils.functional import chunks as _chunks
from celery.utils.functional import (is_list, lookahead, maybe_list, regen,
                                     seq_concat_item, seq_concat_seq)
from celery.utils.objects import getitem_property
from celery.utils.text import remove_repeating_from_task, truncate

__all__ = (
    'Signature', 'chain', 'xmap', 'xstarmap', 'chunks',
    'group', 'chord', 'signature', 'maybe_signature',
)


def maybe_unroll_group(group):
    """Unroll group with only one member."""
    # Issue #1656
    try:
        size = len(group.tasks)
    except TypeError:
        try:
            size = group.tasks.__length_hint__()
        except (AttributeError, TypeError):
            return group
        else:
            return list(group.tasks)[0] if size == 1 else group
    else:
        return group.tasks[0] if size == 1 else group


def task_name_from(task):
    return getattr(task, 'name', task)


@abstract.CallableSignature.register
class Signature(dict):
    """Task Signature.

    Class that wraps the arguments and execution options
    for a single task invocation.

    Used as the parts in a :class:`group` and other constructs,
    or to pass tasks around as callbacks while being compatible
    with serializers with a strict type subset.

    Signatures can also be created from tasks:

    - Using the ``.signature()`` method that has the same signature
      as ``Task.apply_async``:

        .. code-block:: pycon

            >>> add.signature(args=(1,), kwargs={'kw': 2}, options={})

    - or the ``.s()`` shortcut that works for star arguments:

        .. code-block:: pycon

            >>> add.s(1, kw=2)

    - the ``.s()`` shortcut does not allow you to specify execution options
      but there's a chaning `.set` method that returns the signature:

        .. code-block:: pycon

            >>> add.s(2, 2).set(countdown=10).set(expires=30).delay()

    Note:
        You should use :func:`~celery.signature` to create new signatures.
        The ``Signature`` class is the type returned by that function and
        should be used for ``isinstance`` checks for signatures.

    See Also:
        :ref:`guide-canvas` for the complete guide.

    Arguments:
        task (Union[Type[celery.app.task.Task], str]): Either a task
            class/instance, or the name of a task.
        args (Tuple): Positional arguments to apply.
        kwargs (Dict): Keyword arguments to apply.
        options (Dict): Additional options to :meth:`Task.apply_async`.

    Note:
        If the first argument is a :class:`dict`, the other
        arguments will be ignored and the values in the dict will be used
        instead::

            >>> s = signature('tasks.add', args=(2, 2))
            >>> signature(s)
            {'task': 'tasks.add', args=(2, 2), kwargs={}, options={}}
    """

    TYPES = {}
    _app = _type = None
    # The following fields must not be changed during freezing/merging because
    # to do so would disrupt completion of parent tasks
    _IMMUTABLE_OPTIONS = {"group_id"}

    @classmethod
    def register_type(cls, name=None):
        def _inner(subclass):
            cls.TYPES[name or subclass.__name__] = subclass
            return subclass

        return _inner

    @classmethod
    def from_dict(cls, d, app=None):
        typ = d.get('subtask_type')
        if typ:
            target_cls = cls.TYPES[typ]
            if target_cls is not cls:
                return target_cls.from_dict(d, app=app)
        return Signature(d, app=app)

    def __init__(self, task=None, args=None, kwargs=None, options=None,
                 type=None, subtask_type=None, immutable=False,
                 app=None, **ex):
        self._app = app

        if isinstance(task, dict):
            super().__init__(task)  # works like dict(d)
        else:
            # Also supports using task class/instance instead of string name.
            try:
                task_name = task.name
            except AttributeError:
                task_name = task
            else:
                self._type = task

            super().__init__(
                task=task_name, args=tuple(args or ()),
                kwargs=kwargs or {},
                options=dict(options or {}, **ex),
                subtask_type=subtask_type,
                immutable=immutable,
            )

    def __call__(self, *partial_args, **partial_kwargs):
        """Call the task directly (in the current process)."""
        args, kwargs, _ = self._merge(partial_args, partial_kwargs, None)
        return self.type(*args, **kwargs)

    def delay(self, *partial_args, **partial_kwargs):
        """Shortcut to :meth:`apply_async` using star arguments."""
        return self.apply_async(partial_args, partial_kwargs)

    def apply(self, args=None, kwargs=None, **options):
        """Call task locally.

        Same as :meth:`apply_async` but executed the task inline instead
        of sending a task message.
        """
        args = args if args else ()
        kwargs = kwargs if kwargs else {}
        # Extra options set to None are dismissed
        options = {k: v for k, v in options.items() if v is not None}
        # For callbacks: extra args are prepended to the stored args.
        args, kwargs, options = self._merge(args, kwargs, options)
        return self.type.apply(args, kwargs, **options)

    def apply_async(self, args=None, kwargs=None, route_name=None, **options):
        """Apply this task asynchronously.

        Arguments:
            args (Tuple): Partial args to be prepended to the existing args.
            kwargs (Dict): Partial kwargs to be merged with existing kwargs.
            options (Dict): Partial options to be merged
                with existing options.

        Returns:
            ~@AsyncResult: promise of future evaluation.

        See also:
            :meth:`~@Task.apply_async` and the :ref:`guide-calling` guide.
        """
        args = args if args else ()
        kwargs = kwargs if kwargs else {}
        # Extra options set to None are dismissed
        options = {k: v for k, v in options.items() if v is not None}
        try:
            _apply = self._apply_async
        except IndexError:  # pragma: no cover
            # no tasks for chain, etc to find type
            return
        # For callbacks: extra args are prepended to the stored args.
        if args or kwargs or options:
            args, kwargs, options = self._merge(args, kwargs, options)
        else:
            args, kwargs, options = self.args, self.kwargs, self.options
        # pylint: disable=too-many-function-args
        #   Borks on this, as it's a property
        return _apply(args, kwargs, **options)

    def _merge(self, args=None, kwargs=None, options=None, force=False):
        args = args if args else ()
        kwargs = kwargs if kwargs else {}
        if options is not None:
            # We build a new options dictionary where values in `options`
            # override values in `self.options` except for keys which are
            # noted as being immutable (unrelated to signature immutability)
            # implying that allowing their value to change would stall tasks
            new_options = dict(self.options, **{
                k: v for k, v in options.items()
                if k not in self._IMMUTABLE_OPTIONS or k not in self.options
            })
        else:
            new_options = self.options
        if self.immutable and not force:
            return (self.args, self.kwargs, new_options)
        return (tuple(args) + tuple(self.args) if args else self.args,
                dict(self.kwargs, **kwargs) if kwargs else self.kwargs,
                new_options)

    def clone(self, args=None, kwargs=None, **opts):
        """Create a copy of this signature.

        Arguments:
            args (Tuple): Partial args to be prepended to the existing args.
            kwargs (Dict): Partial kwargs to be merged with existing kwargs.
            options (Dict): Partial options to be merged with
                existing options.
        """
        args = args if args else ()
        kwargs = kwargs if kwargs else {}
        # need to deepcopy options so origins links etc. is not modified.
        if args or kwargs or opts:
            args, kwargs, opts = self._merge(args, kwargs, opts)
        else:
            args, kwargs, opts = self.args, self.kwargs, self.options
        signature = Signature.from_dict({'task': self.task,
                                         'args': tuple(args),
                                         'kwargs': kwargs,
                                         'options': deepcopy(opts),
                                         'subtask_type': self.subtask_type,
                                         'immutable': self.immutable},
                                        app=self._app)
        signature._type = self._type
        return signature

    partial = clone

    def freeze(self, _id=None, group_id=None, chord=None,
               root_id=None, parent_id=None, group_index=None):
        """Finalize the signature by adding a concrete task id.

        The task won't be called and you shouldn't call the signature
        twice after freezing it as that'll result in two task messages
        using the same task id.

        Returns:
            ~@AsyncResult: promise of future evaluation.
        """
        # pylint: disable=redefined-outer-name
        #   XXX chord is also a class in outer scope.
        opts = self.options
        try:
            # if there is already an id for this task, return it
            tid = opts['task_id']
        except KeyError:
            # otherwise, use the _id sent to this function, falling back on a generated UUID
            tid = opts['task_id'] = _id or uuid()
        if root_id:
            opts['root_id'] = root_id
        if parent_id:
            opts['parent_id'] = parent_id
        if 'reply_to' not in opts:
            # fall back on unique ID for this thread in the app
            opts['reply_to'] = self.app.thread_oid
        if group_id and "group_id" not in opts:
            opts['group_id'] = group_id
        if chord:
            opts['chord'] = chord
        if group_index is not None:
            opts['group_index'] = group_index
        # pylint: disable=too-many-function-args
        #   Borks on this, as it's a property.
        return self.AsyncResult(tid)

    _freeze = freeze

    def replace(self, args=None, kwargs=None, options=None):
        """Replace the args, kwargs or options set for this signature.

        These are only replaced if the argument for the section is
        not :const:`None`.
        """
        signature = self.clone()
        if args is not None:
            signature.args = args
        if kwargs is not None:
            signature.kwargs = kwargs
        if options is not None:
            signature.options = options
        return signature

    def set(self, immutable=None, **options):
        """Set arbitrary execution options (same as ``.options.update(…)``).

        Returns:
            Signature: This is a chaining method call
                (i.e., it will return ``self``).
        """
        if immutable is not None:
            self.set_immutable(immutable)
        self.options.update(options)
        return self

    def set_immutable(self, immutable):
        self.immutable = immutable

    def _with_list_option(self, key):
        items = self.options.setdefault(key, [])
        if not isinstance(items, MutableSequence):
            items = self.options[key] = [items]
        return items

    def append_to_list_option(self, key, value):
        items = self._with_list_option(key)
        if value not in items:
            items.append(value)
        return value

    def extend_list_option(self, key, value):
        items = self._with_list_option(key)
        items.extend(maybe_list(value))

    def link(self, callback):
        """Add callback task to be applied if this task succeeds.

        Returns:
            Signature: the argument passed, for chaining
                or use with :func:`~functools.reduce`.
        """
        return self.append_to_list_option('link', callback)

    def link_error(self, errback):
        """Add callback task to be applied on error in task execution.

        Returns:
            Signature: the argument passed, for chaining
                or use with :func:`~functools.reduce`.
        """
        return self.append_to_list_option('link_error', errback)

    def on_error(self, errback):
        """Version of :meth:`link_error` that supports chaining.

        on_error chains the original signature, not the errback so::

            >>> add.s(2, 2).on_error(errback.s()).delay()

        calls the ``add`` task, not the ``errback`` task, but the
        reverse is true for :meth:`link_error`.
        """
        self.link_error(errback)
        return self

    def flatten_links(self):
        """Return a recursive list of dependencies.

        "unchain" if you will, but with links intact.
        """
        return list(itertools.chain.from_iterable(itertools.chain(
            [[self]],
            (link.flatten_links()
             for link in maybe_list(self.options.get('link')) or [])
        )))

    def __or__(self, other):
        if isinstance(other, _chain):
            # task | chain -> chain
            return _chain(seq_concat_seq(
                (self,), other.unchain_tasks()), app=self._app)
        elif isinstance(other, group):
            # unroll group with one member
            other = maybe_unroll_group(other)
            # task | group() -> chain
            return _chain(self, other, app=self.app)
        elif isinstance(other, Signature):
            # task | task -> chain
            return _chain(self, other, app=self._app)
        return NotImplemented

    def __ior__(self, other):
        # Python 3.9 introduces | as the merge operator for dicts.
        # We override the in-place version of that operator
        # so that canvases continue to work as they did before.
        return self.__or__(other)

    def election(self):
        type = self.type
        app = type.app
        tid = self.options.get('task_id') or uuid()

        with app.producer_or_acquire(None) as producer:
            props = type.backend.on_task_call(producer, tid)
            app.control.election(tid, 'task',
                                 self.clone(task_id=tid, **props),
                                 connection=producer.connection)
            return type.AsyncResult(tid)

    def reprcall(self, *args, **kwargs):
        args, kwargs, _ = self._merge(args, kwargs, {}, force=True)
        return reprcall(self['task'], args, kwargs)

    def __deepcopy__(self, memo):
        memo[id(self)] = self
        return dict(self)

    def __invert__(self):
        return self.apply_async().get()

    def __reduce__(self):
        # for serialization, the task type is lazily loaded,
        # and not stored in the dict itself.
        return signature, (dict(self),)

    def __json__(self):
        return dict(self)

    def __repr__(self):
        return self.reprcall()

    def items(self):
        for k, v in super().items():
            yield k.decode() if isinstance(k, bytes) else k, v

    @property
    def name(self):
        # for duck typing compatibility with Task.name
        return self.task

    @cached_property
    def type(self):
        return self._type or self.app.tasks[self['task']]

    @cached_property
    def app(self):
        return self._app or current_app

    @cached_property
    def AsyncResult(self):
        try:
            return self.type.AsyncResult
        except KeyError:  # task not registered
            return self.app.AsyncResult

    @cached_property
    def _apply_async(self):
        try:
            return self.type.apply_async
        except KeyError:
            return _partial(self.app.send_task, self['task'])

    id = getitem_property('options.task_id', 'Task UUID')
    parent_id = getitem_property('options.parent_id', 'Task parent UUID.')
    root_id = getitem_property('options.root_id', 'Task root UUID.')
    task = getitem_property('task', 'Name of task.')
    args = getitem_property('args', 'Positional arguments to task.')
    kwargs = getitem_property('kwargs', 'Keyword arguments to task.')
    options = getitem_property('options', 'Task execution options.')
    subtask_type = getitem_property('subtask_type', 'Type of signature')
    immutable = getitem_property(
        'immutable', 'Flag set if no longer accepts new arguments')


def _prepare_chain_from_options(options, tasks, use_link):
    # When we publish groups we reuse the same options dictionary for all of
    # the tasks in the group. See:
    # https://github.com/celery/celery/blob/fb37cb0b8/celery/canvas.py#L1022.
    # Issue #5354 reported that the following type of canvases
    # causes a Celery worker to hang:
    # group(
    #   add.s(1, 1),
    #   add.s(1, 1)
    # ) | tsum.s() | add.s(1) | group(add.s(1), add.s(1))
    # The resolution of #5354 in PR #5681 was to only set the `chain` key
    # in the options dictionary if it is not present.
    # Otherwise we extend the existing list of tasks in the chain with the new
    # tasks: options['chain'].extend(chain_).
    # Before PR #5681 we overrode the `chain` key in each iteration
    # of the loop which applies all the tasks in the group:
    # options['chain'] = tasks if not use_link else None
    # This caused Celery to execute chains correctly in most cases since
    # in each iteration the `chain` key would reset itself to a new value
    # and the side effect of mutating the key did not propagate
    # to the next task in the group.
    # Since we now mutated the `chain` key, a *list* which is passed
    # by *reference*, the next task in the group will extend the list
    # of tasks in the chain instead of setting a new one from the chain_
    # variable above.
    # This causes Celery to execute a chain, even though there might not be
    # one to begin with. Alternatively, it causes Celery to execute more tasks
    # that were previously present in the previous task in the group.
    # The solution is to be careful and never mutate the options dictionary
    # to begin with.
    # Here is an example of a canvas which triggers this issue:
    # add.s(5, 6) | group((add.s(1) | add.s(2), add.s(3))).
    # The expected result is [14, 14]. However, when we extend the `chain`
    # key the `add.s(3)` task erroneously has `add.s(2)` in its chain since
    # it was previously applied to `add.s(1)`.
    # Without being careful not to mutate the options dictionary, the result
    # in this case is [16, 14].
    # To avoid deep-copying the entire options dictionary every single time we
    # run a chain we use a ChainMap and ensure that we never mutate
    # the original `chain` key, hence we use list_a + list_b to create a new
    # list.
    if use_link:
        return ChainMap({'chain': None}, options)
    elif 'chain' not in options:
        return ChainMap({'chain': tasks}, options)
    elif tasks is not None:
        # chain option may already be set, resulting in
        # "multiple values for keyword argument 'chain'" error.
        # Issue #3379.
        # If a chain already exists, we need to extend it with the next
        # tasks in the chain.
        # Issue #5354.
        # WARNING: Be careful not to mutate `options['chain']`.
        return ChainMap({'chain': options['chain'] + tasks},
                        options)


@Signature.register_type(name='chain')
class _chain(Signature):
    tasks = getitem_property('kwargs.tasks', 'Tasks in chain.')

    @classmethod
    def from_dict(cls, d, app=None):
        tasks = d['kwargs']['tasks']
        if tasks:
            if isinstance(tasks, tuple):  # aaaargh
                tasks = d['kwargs']['tasks'] = list(tasks)
            tasks = [maybe_signature(task, app=app) for task in tasks]
        return _chain(tasks, app=app, **d['options'])

    def __init__(self, *tasks, **options):
        tasks = (regen(tasks[0]) if len(tasks) == 1 and is_list(tasks[0])
                 else tasks)
        super().__init__('celery.chain', (), {'tasks': tasks}, **options
                         )
        self._use_link = options.pop('use_link', None)
        self.subtask_type = 'chain'
        self._frozen = None

    def __call__(self, *args, **kwargs):
        if self.tasks:
            return self.apply_async(args, kwargs)

    def __or__(self, other):
        if isinstance(other, group):
            # unroll group with one member
            other = maybe_unroll_group(other)
            # chain | group() -> chain
            tasks = self.unchain_tasks()
            if not tasks:
                # If the chain is empty, return the group
                return other
            return _chain(seq_concat_item(
                tasks, other), app=self._app)
        elif isinstance(other, _chain):
            # chain | chain -> chain
            return _chain(seq_concat_seq(
                self.unchain_tasks(), other.unchain_tasks()), app=self._app)
        elif isinstance(other, Signature):
            if self.tasks and isinstance(self.tasks[-1], group):
                # CHAIN [last item is group] | TASK -> chord
                sig = self.clone()
                sig.tasks[-1] = chord(
                    sig.tasks[-1], other, app=self._app)
                return sig
            elif self.tasks and isinstance(self.tasks[-1], chord):
                # CHAIN [last item is chord] -> chain with chord body.
                sig = self.clone()
                sig.tasks[-1].body = sig.tasks[-1].body | other
                return sig
            else:
                # chain | task -> chain
                return _chain(seq_concat_item(
                    self.unchain_tasks(), other), app=self._app)
        else:
            return NotImplemented

    def clone(self, *args, **kwargs):
        to_signature = maybe_signature
        signature = super().clone(*args, **kwargs)
        signature.kwargs['tasks'] = [
            to_signature(sig, app=self._app, clone=True)
            for sig in signature.kwargs['tasks']
        ]
        return signature

    def unchain_tasks(self):
        # Clone chain's tasks assigning signatures from link_error
        # to each task
        tasks = [t.clone() for t in self.tasks]
        for sig in self.options.get('link_error', []):
            for task in tasks:
                task.link_error(sig)
        return tasks

    def apply_async(self, args=None, kwargs=None, **options):
        # python is best at unpacking kwargs, so .run is here to do that.
        args = args if args else ()
        kwargs = kwargs if kwargs else []
        app = self.app
        if app.conf.task_always_eager:
            with allow_join_result():
                return self.apply(args, kwargs, **options)
        return self.run(args, kwargs, app=app, **(
            dict(self.options, **options) if options else self.options))

    def run(self, args=None, kwargs=None, group_id=None, chord=None,
            task_id=None, link=None, link_error=None, publisher=None,
            producer=None, root_id=None, parent_id=None, app=None,
            group_index=None, **options):
        # pylint: disable=redefined-outer-name
        #   XXX chord is also a class in outer scope.
        args = args if args else ()
        kwargs = kwargs if kwargs else []
        app = app or self.app
        use_link = self._use_link
        if use_link is None and app.conf.task_protocol == 1:
            use_link = True
        args = (tuple(args) + tuple(self.args)
                if args and not self.immutable else self.args)

        tasks, results_from_prepare = self.prepare_steps(
            args, kwargs, self.tasks, root_id, parent_id, link_error, app,
            task_id, group_id, chord, group_index=group_index,
        )

        if results_from_prepare:
            if link:
                tasks[0].extend_list_option('link', link)
            first_task = tasks.pop()
            options = _prepare_chain_from_options(options, tasks, use_link)

            result_from_apply = first_task.apply_async(**options)
            # If we only have a single task, it may be important that we pass
            # the real result object rather than the one obtained via freezing.
            # e.g. For `GroupResult`s, we need to pass back the result object
            # which will actually have its promise fulfilled by the subtasks,
            # something that will never occur for the frozen result.
            if not tasks:
                return result_from_apply
            else:
                return results_from_prepare[0]

    # in order for a chain to be frozen, each of the members of the chain individually needs to be frozen
    # TODO figure out why we are always cloning before freeze
    def freeze(self, _id=None, group_id=None, chord=None,
               root_id=None, parent_id=None, group_index=None):
        # pylint: disable=redefined-outer-name
        #   XXX chord is also a class in outer scope.
        _, results = self._frozen = self.prepare_steps(
            self.args, self.kwargs, self.tasks, root_id, parent_id, None,
            self.app, _id, group_id, chord, clone=False,
            group_index=group_index,
        )
        return results[0]

    def prepare_steps(self, args, kwargs, tasks,
                      root_id=None, parent_id=None, link_error=None, app=None,
                      last_task_id=None, group_id=None, chord_body=None,
                      clone=True, from_dict=Signature.from_dict,
                      group_index=None):
        app = app or self.app
        # use chain message field for protocol 2 and later.
        # this avoids pickle blowing the stack on the recursion
        # required by linking task together in a tree structure.
        # (why is pickle using recursion? or better yet why cannot python
        #  do tail call optimization making recursion actually useful?)
        use_link = self._use_link
        if use_link is None and app.conf.task_protocol == 1:
            use_link = True
        steps = deque(tasks)

        # optimization: now the pop func is a local variable
        steps_pop = steps.pop
        steps_extend = steps.extend

        prev_task = None
        prev_res = None
        tasks, results = [], []
        i = 0
        # NOTE: We are doing this in reverse order.
        # The result is a list of tasks in reverse order, that is
        # passed as the ``chain`` message field.
        # As it's reversed the worker can just do ``chain.pop()`` to
        # get the next task in the chain.
        while steps:
            task = steps_pop()
            # if steps is not empty, this is the first task - reverse order
            # if i = 0, this is the last task - again, because we're reversed
            is_first_task, is_last_task = not steps, not i

            if not isinstance(task, abstract.CallableSignature):
                task = from_dict(task, app=app)
            if isinstance(task, group):
                # when groups are nested, they are unrolled - all tasks within
                # groups within groups should be called in parallel
                task = maybe_unroll_group(task)

            # first task gets partial args from chain
            if clone:
                if is_first_task:
                    task = task.clone(args, kwargs)
                else:
                    task = task.clone()
            elif is_first_task:
                task.args = tuple(args) + tuple(task.args)

            if isinstance(task, _chain):
                # splice (unroll) the chain
                steps_extend(task.tasks)
                continue

            # TODO why isn't this asserting is_last_task == False?
            if isinstance(task, group) and prev_task:
                # automatically upgrade group(...) | s to chord(group, s)
                # for chords we freeze by pretending it's a normal
                # signature instead of a group.
                tasks.pop()
                results.pop()
                try:
                    task = chord(
                        task, body=prev_task,
                        task_id=prev_res.task_id, root_id=root_id, app=app,
                    )
                except AttributeError:
                    # A GroupResult does not have a task_id since it consists
                    # of multiple tasks.
                    # We therefore, have to construct the chord without it.
                    # Issues #5467, #3585.
                    task = chord(
                        task, body=prev_task,
                        root_id=root_id, app=app,
                    )

            if is_last_task:
                # chain(task_id=id) means task id is set for the last task
                # in the chain.  If the chord is part of a chord/group
                # then that chord/group must synchronize based on the
                # last task in the chain, so we only set the group_id and
                # chord callback for the last task.
                res = task.freeze(
                    last_task_id,
                    root_id=root_id, group_id=group_id, chord=chord_body,
                    group_index=group_index,
                )
            else:
                res = task.freeze(root_id=root_id)

            i += 1

            if prev_task:
                if use_link:
                    # link previous task to this task.
                    task.link(prev_task)

                if prev_res and not prev_res.parent:
                    prev_res.parent = res

            if link_error:
                for errback in maybe_list(link_error):
                    task.link_error(errback)

            tasks.append(task)
            results.append(res)

            prev_task, prev_res = task, res
            if isinstance(task, chord):
                app.backend.ensure_chords_allowed()
                # If the task is a chord, and the body is a chain
                # the chain has already been prepared, and res is
                # set to the last task in the callback chain.

                # We need to change that so that it points to the
                # group result object.
                node = res
                while node.parent:
                    node = node.parent
                prev_res = node
        return tasks, results

    def apply(self, args=None, kwargs=None, **options):
        args = args if args else ()
        kwargs = kwargs if kwargs else {}
        last, (fargs, fkwargs) = None, (args, kwargs)
        for task in self.tasks:
            res = task.clone(fargs, fkwargs).apply(
                last and (last.get(),), **dict(self.options, **options))
            res.parent, last, (fargs, fkwargs) = last, res, (None, None)
        return last

    @property
    def app(self):
        app = self._app
        if app is None:
            try:
                app = self.tasks[0]._app
            except LookupError:
                pass
        return app or current_app

    def __repr__(self):
        if not self.tasks:
            return f'<{type(self).__name__}@{id(self):#x}: empty>'
        return remove_repeating_from_task(
            self.tasks[0]['task'],
            ' | '.join(repr(t) for t in self.tasks))


class chain(_chain):
    """Chain tasks together.

    Each tasks follows one another,
    by being applied as a callback of the previous task.

    Note:
        If called with only one argument, then that argument must
        be an iterable of tasks to chain: this allows us
        to use generator expressions.

    Example:
        This is effectively :math:`((2 + 2) + 4)`:

        .. code-block:: pycon

            >>> res = chain(add.s(2, 2), add.s(4))()
            >>> res.get()
            8

        Calling a chain will return the result of the last task in the chain.
        You can get to the other tasks by following the ``result.parent``'s:

        .. code-block:: pycon

            >>> res.parent.get()
            4

        Using a generator expression:

        .. code-block:: pycon

            >>> lazy_chain = chain(add.s(i) for i in range(10))
            >>> res = lazy_chain(3)

    Arguments:
        *tasks (Signature): List of task signatures to chain.
            If only one argument is passed and that argument is
            an iterable, then that'll be used as the list of signatures
            to chain instead.  This means that you can use a generator
            expression.

    Returns:
        ~celery.chain: A lazy signature that can be called to apply the first
            task in the chain.  When that task succeeds the next task in the
            chain is applied, and so on.
    """

    # could be function, but must be able to reference as :class:`chain`.
    def __new__(cls, *tasks, **kwargs):
        # This forces `chain(X, Y, Z)` to work the same way as `X | Y | Z`
        if not kwargs and tasks:
            if len(tasks) != 1 or is_list(tasks[0]):
                tasks = tasks[0] if len(tasks) == 1 else tasks
                # if is_list(tasks) and len(tasks) == 1:
                #     return super(chain, cls).__new__(cls, tasks, **kwargs)
                return reduce(operator.or_, tasks, chain())
        return super().__new__(cls, *tasks, **kwargs)


class _basemap(Signature):
    _task_name = None
    _unpack_args = itemgetter('task', 'it')

    @classmethod
    def from_dict(cls, d, app=None):
        return cls(*cls._unpack_args(d['kwargs']), app=app, **d['options'])

    def __init__(self, task, it, **options):
        super().__init__(self._task_name, (),
                         {'task': task, 'it': regen(it)}, immutable=True, **options
                         )

    def apply_async(self, args=None, kwargs=None, **opts):
        # need to evaluate generators
        args = args if args else ()
        kwargs = kwargs if kwargs else {}
        task, it = self._unpack_args(self.kwargs)
        return self.type.apply_async(
            (), {'task': task, 'it': list(it)},
            route_name=task_name_from(self.kwargs.get('task')), **opts
        )


@Signature.register_type()
class xmap(_basemap):
    """Map operation for tasks.

    Note:
        Tasks executed sequentially in process, this is not a
        parallel operation like :class:`group`.
    """

    _task_name = 'celery.map'

    def __repr__(self):
        task, it = self._unpack_args(self.kwargs)
        return f'[{task.task}(x) for x in {truncate(repr(it), 100)}]'


@Signature.register_type()
class xstarmap(_basemap):
    """Map operation for tasks, using star arguments."""

    _task_name = 'celery.starmap'

    def __repr__(self):
        task, it = self._unpack_args(self.kwargs)
        return f'[{task.task}(*x) for x in {truncate(repr(it), 100)}]'


@Signature.register_type()
class chunks(Signature):
    """Partition of tasks into chunks of size n."""

    _unpack_args = itemgetter('task', 'it', 'n')

    @classmethod
    def from_dict(cls, d, app=None):
        return chunks(*cls._unpack_args(d['kwargs']), app=app, **d['options'])

    def __init__(self, task, it, n, **options):
        super().__init__('celery.chunks', (),
                         {'task': task, 'it': regen(it), 'n': n},
                         immutable=True, **options
                         )

    def __call__(self, **options):
        return self.apply_async(**options)

    def apply_async(self, args=None, kwargs=None, **opts):
        args = args if args else ()
        kwargs = kwargs if kwargs else {}
        return self.group().apply_async(
            args, kwargs,
            route_name=task_name_from(self.kwargs.get('task')), **opts
        )

    def group(self):
        # need to evaluate generators
        task, it, n = self._unpack_args(self.kwargs)
        return group((xstarmap(task, part, app=self._app)
                      for part in _chunks(iter(it), n)),
                     app=self._app)

    @classmethod
    def apply_chunks(cls, task, it, n, app=None):
        return cls(task, it, n, app=app)()


def _maybe_group(tasks, app):
    if isinstance(tasks, dict):
        tasks = signature(tasks, app=app)

    if isinstance(tasks, (group, _chain)):
        tasks = tasks.tasks
    elif isinstance(tasks, abstract.CallableSignature):
        tasks = [tasks]
    else:
        if isinstance(tasks, GeneratorType):
            tasks = regen(signature(t, app=app) for t in tasks)
        else:
            tasks = [signature(t, app=app) for t in tasks]
    return tasks


@Signature.register_type()
class group(Signature):
    """Creates a group of tasks to be executed in parallel.

    A group is lazy so you must call it to take action and evaluate
    the group.

    Note:
        If only one argument is passed, and that argument is an iterable
        then that'll be used as the list of tasks instead: this
        allows us to use ``group`` with generator expressions.

    Example:
        >>> lazy_group = group([add.s(2, 2), add.s(4, 4)])
        >>> promise = lazy_group()  # <-- evaluate: returns lazy result.
        >>> promise.get()  # <-- will wait for the task to return
        [4, 8]

    Arguments:
        *tasks (List[Signature]): A list of signatures that this group will
            call. If there's only one argument, and that argument is an
            iterable, then that'll define the list of signatures instead.
        **options (Any): Execution options applied to all tasks
            in the group.

    Returns:
        ~celery.group: signature that when called will then call all of the
            tasks in the group (and return a :class:`GroupResult` instance
            that can be used to inspect the state of the group).
    """

    tasks = getitem_property('kwargs.tasks', 'Tasks in group.')

    @classmethod
    def from_dict(cls, d, app=None):
        # We need to mutate the `kwargs` element in place to avoid confusing
        # `freeze()` implementations which end up here and expect to be able to
        # access elements from that dictionary later and refer to objects
        # canonicalized here
        orig_tasks = d["kwargs"]["tasks"]
        d["kwargs"]["tasks"] = rebuilt_tasks = type(orig_tasks)(
            maybe_signature(task, app=app) for task in orig_tasks
        )
        return group(rebuilt_tasks, app=app, **d['options'])

    def __init__(self, *tasks, **options):
        if len(tasks) == 1:
            tasks = tasks[0]
            if isinstance(tasks, group):
                tasks = tasks.tasks
            if isinstance(tasks, abstract.CallableSignature):
                tasks = [tasks.clone()]
            if not isinstance(tasks, _regen):
                tasks = regen(tasks)
        super().__init__('celery.group', (), {'tasks': tasks}, **options
                         )
        self.subtask_type = 'group'

    def __call__(self, *partial_args, **options):
        return self.apply_async(partial_args, **options)

    def __or__(self, other):
        # group() | task -> chord
        return chord(self, body=other, app=self._app)

    def skew(self, start=1.0, stop=None, step=1.0):
        it = fxrange(start, stop, step, repeatlast=True)
        for task in self.tasks:
            task.set(countdown=next(it))
        return self

    def apply_async(self, args=None, kwargs=None, add_to_parent=True,
                    producer=None, link=None, link_error=None, **options):
        args = args if args else ()
        if link is not None:
            raise TypeError('Cannot add link to group: use a chord')
        if link_error is not None:
            raise TypeError(
                'Cannot add link to group: do that on individual tasks')
        app = self.app
        if app.conf.task_always_eager:
            return self.apply(args, kwargs, **options)
        if not self.tasks:
            return self.freeze()

        options, group_id, root_id = self._freeze_gid(options)
        tasks = self._prepared(self.tasks, [], group_id, root_id, app)
        p = barrier()
        results = list(self._apply_tasks(tasks, producer, app, p,
                                         args=args, kwargs=kwargs, **options))
        result = self.app.GroupResult(group_id, results, ready_barrier=p)
        p.finalize()

        # - Special case of group(A.s() | group(B.s(), C.s()))
        # That is, group with single item that's a chain but the
        # last task in that chain is a group.
        #
        # We cannot actually support arbitrary GroupResults in chains,
        # but this special case we can.
        if len(result) == 1 and isinstance(result[0], GroupResult):
            result = result[0]

        parent_task = app.current_worker_task
        if add_to_parent and parent_task:
            parent_task.add_trail(result)
        return result

    def apply(self, args=None, kwargs=None, **options):
        args = args if args else ()
        kwargs = kwargs if kwargs else {}
        app = self.app
        if not self.tasks:
            return self.freeze()  # empty group returns GroupResult
        options, group_id, root_id = self._freeze_gid(options)
        tasks = self._prepared(self.tasks, [], group_id, root_id, app)
        return app.GroupResult(group_id, [
            sig.apply(args=args, kwargs=kwargs, **options) for sig, _, _ in tasks
        ])

    def set_immutable(self, immutable):
        for task in self.tasks:
            task.set_immutable(immutable)

    def link(self, sig):
        # Simply link to first task. Doing this is slightly misleading because
        # the callback may be executed before all children in the group are
        # completed and also if any children other than the first one fail.
        #
        # The callback signature is cloned and made immutable since it the
        # first task isn't actually capable of passing the return values of its
        # siblings to the callback task.
        sig = sig.clone().set(immutable=True)
        return self.tasks[0].link(sig)

    def link_error(self, sig):
        # Any child task might error so we need to ensure that they are all
        # capable of calling the linked error signature. This opens the
        # possibility that the task is called more than once but that's better
        # than it not being called at all.
        #
        # We return a concretised tuple of the signatures actually applied to
        # each child task signature, of which there might be none!
        return tuple(child_task.link_error(sig) for child_task in self.tasks)

    def _prepared(self, tasks, partial_args, group_id, root_id, app,
                  CallableSignature=abstract.CallableSignature,
                  from_dict=Signature.from_dict,
                  isinstance=isinstance, tuple=tuple):
        for task in tasks:
            if isinstance(task, CallableSignature):
                # local sigs are always of type Signature, and we
                # clone them to make sure we don't modify the originals.
                task = task.clone()
            else:
                # serialized sigs must be converted to Signature.
                task = from_dict(task, app=app)
            if isinstance(task, group):
                # needs yield_from :(
                unroll = task._prepared(
                    task.tasks, partial_args, group_id, root_id, app,
                )
                yield from unroll
            else:
                if partial_args and not task.immutable:
                    task.args = tuple(partial_args) + tuple(task.args)
                yield task, task.freeze(group_id=group_id, root_id=root_id), group_id

    def _apply_tasks(self, tasks, producer=None, app=None, p=None,
                     add_to_parent=None, chord=None,
                     args=None, kwargs=None, **options):
        # pylint: disable=redefined-outer-name
        #   XXX chord is also a class in outer scope.
        app = app or self.app
        with app.producer_or_acquire(producer) as producer:
            # Iterate through tasks two at a time. If tasks is a generator,
            # we are able to tell when we are at the end by checking if
            # next_task is None.  This enables us to set the chord size
            # without burning through the entire generator.  See #3021.
            chord_size = 0
            for task_index, (current_task, next_task) in enumerate(
                lookahead(tasks)
            ):
                # We expect that each task must be part of the same group which
                # seems sensible enough. If that's somehow not the case we'll
                # end up messing up chord counts and there are all sorts of
                # awful race conditions to think about. We'll hope it's not!
                sig, res, group_id = current_task
                chord_obj = chord if chord is not None else sig.options.get("chord")
                # We need to check the chord size of each contributing task so
                # that when we get to the final one, we can correctly set the
                # size in the backend and the chord can be sensible completed.
                chord_size += _chord._descend(sig)
                if chord_obj is not None and next_task is None:
                    # Per above, sanity check that we only saw one group
                    app.backend.set_chord_size(group_id, chord_size)
                sig.apply_async(producer=producer, add_to_parent=False,
                                chord=chord_obj, args=args, kwargs=kwargs,
                                **options)
                # adding callback to result, such that it will gradually
                # fulfill the barrier.
                #
                # Using barrier.add would use result.then, but we need
                # to add the weak argument here to only create a weak
                # reference to the object.
                if p and not p.cancelled and not p.ready:
                    p.size += 1
                    res.then(p, weak=True)
                yield res  # <-- r.parent, etc set in the frozen result.

    def _freeze_gid(self, options):
        # remove task_id and use that as the group_id,
        # if we don't remove it then every task will have the same id...
        options = dict(self.options, **options)
        options['group_id'] = group_id = (
            options.pop('task_id', uuid()))
        return options, group_id, options.get('root_id')

    def _freeze_group_tasks(self, _id=None, group_id=None, chord=None,
                            root_id=None, parent_id=None, group_index=None):
        # pylint: disable=redefined-outer-name
        #  XXX chord is also a class in outer scope.
        opts = self.options
        try:
            gid = opts['task_id']
        except KeyError:
            gid = opts['task_id'] = group_id or uuid()
        if group_id:
            opts['group_id'] = group_id
        if chord:
            opts['chord'] = chord
        if group_index is not None:
            opts['group_index'] = group_index
        root_id = opts.setdefault('root_id', root_id)
        parent_id = opts.setdefault('parent_id', parent_id)
        if isinstance(self.tasks, _regen):
            # We are draining from a generator here.
            # tasks1, tasks2 are each a clone of self.tasks
            tasks1, tasks2 = itertools.tee(self._unroll_tasks(self.tasks))
            # freeze each task in tasks1, results now holds AsyncResult for each task
            results = regen(self._freeze_tasks(tasks1, group_id, chord, root_id, parent_id))
            # TODO figure out why this makes sense -
            # we freeze all tasks in the clone tasks1, and then zip the results
            # with the IDs of tasks in the second clone, tasks2. and then, we build
            # a generator that takes only the task IDs from tasks2.
            self.tasks = regen(x[0] for x in zip(tasks2, results))
        else:
            new_tasks = []
            # Need to unroll subgroups early so that chord gets the
            # right result instance for chord_unlock etc.
            results = list(self._freeze_unroll(
                new_tasks, group_id, chord, root_id, parent_id,
            ))
            if isinstance(self.tasks, MutableSequence):
                self.tasks[:] = new_tasks
            else:
                self.tasks = new_tasks
        return gid, results

    def freeze(self, _id=None, group_id=None, chord=None,
               root_id=None, parent_id=None, group_index=None):
        return self.app.GroupResult(*self._freeze_group_tasks(
            _id=_id, group_id=group_id,
            chord=chord, root_id=root_id, parent_id=parent_id, group_index=group_index
        ))

    _freeze = freeze

    def _freeze_tasks(self, tasks, group_id, chord, root_id, parent_id):
        yield from (task.freeze(group_id=group_id,
                                chord=chord,
                                root_id=root_id,
                                parent_id=parent_id,
                                group_index=group_index)
                    for group_index, task in enumerate(tasks))

    def _unroll_tasks(self, tasks):
        # should be refactored to: (maybe_signature(task, app=self._app, clone=True) for task in tasks)
        yield from (maybe_signature(task, app=self._app).clone() for task in tasks)

    def _freeze_unroll(self, new_tasks, group_id, chord, root_id, parent_id):
        # pylint: disable=redefined-outer-name
        #   XXX chord is also a class in outer scope.
        stack = deque(self.tasks)
        group_index = 0
        while stack:
            task = maybe_signature(stack.popleft(), app=self._app).clone()
            # if this is a group, flatten it by adding all of the group's tasks to the stack
            if isinstance(task, group):
                stack.extendleft(task.tasks)
            else:
                new_tasks.append(task)
                yield task.freeze(group_id=group_id,
                                  chord=chord, root_id=root_id,
                                  parent_id=parent_id,
                                  group_index=group_index)
                group_index += 1

    def __repr__(self):
        if self.tasks:
            return remove_repeating_from_task(
                self.tasks[0]['task'],
                f'group({self.tasks!r})')
        return 'group(<empty>)'

    def __len__(self):
        return len(self.tasks)

    @property
    def app(self):
        app = self._app
        if app is None:
            try:
                app = self.tasks[0].app
            except LookupError:
                pass
        return app if app is not None else current_app


@Signature.register_type(name="chord")
class _chord(Signature):
    r"""Barrier synchronization primitive.

    A chord consists of a header and a body.

    The header is a group of tasks that must complete before the callback is
    called.  A chord is essentially a callback for a group of tasks.

    The body is applied with the return values of all the header
    tasks as a list.

    Example:

        The chord:

        .. code-block:: pycon

            >>> res = chord([add.s(2, 2), add.s(4, 4)])(sum_task.s())

        is effectively :math:`\Sigma ((2 + 2) + (4 + 4))`:

        .. code-block:: pycon

            >>> res.get()
            12
    """

    @classmethod
    def from_dict(cls, d, app=None):
        options = d.copy()
        args, options['kwargs'] = cls._unpack_args(**options['kwargs'])
        return cls(*args, app=app, **options)

    @staticmethod
    def _unpack_args(header=None, body=None, **kwargs):
        # Python signatures are better at extracting keys from dicts
        # than manually popping things off.
        return (header, body), kwargs

    def __init__(self, header, body=None, task='celery.chord',
                 args=None, kwargs=None, app=None, **options):
        args = args if args else ()
        kwargs = kwargs if kwargs else {'kwargs': {}}
        super().__init__(task, args,
                         {**kwargs, 'header': _maybe_group(header, app),
                          'body': maybe_signature(body, app=app)}, app=app, **options
                         )
        self.subtask_type = 'chord'

    def __call__(self, body=None, **options):
        return self.apply_async((), {'body': body} if body else {}, **options)

    def __or__(self, other):
        if (not isinstance(other, (group, _chain)) and
           isinstance(other, Signature)):
            # chord | task ->  attach to body
            sig = self.clone()
            sig.body = sig.body | other
            return sig
        else:
            return super().__or__(other)

    def freeze(self, _id=None, group_id=None, chord=None,
               root_id=None, parent_id=None, group_index=None):
        # pylint: disable=redefined-outer-name
        #   XXX chord is also a class in outer scope.
        if not isinstance(self.tasks, group):
            self.tasks = group(self.tasks, app=self.app)
        # first freeze all tasks in the header
        header_result = self.tasks.freeze(
            parent_id=parent_id, root_id=root_id, chord=self.body)
        # secondly freeze all tasks in the body: those that should be called after the header
        body_result = self.body.freeze(
            _id, root_id=root_id, chord=chord, group_id=group_id,
            group_index=group_index)
        # we need to link the body result back to the group result,
        # but the body may actually be a chain,
        # so find the first result without a parent
        node = body_result
        seen = set()
        while node:
            if node.id in seen:
                raise RuntimeError('Recursive result parents')
            seen.add(node.id)
            if node.parent is None:
                node.parent = header_result
                break
            node = node.parent
        self.id = self.tasks.id
        return body_result

    def apply_async(self, args=None, kwargs=None, task_id=None,
                    producer=None, publisher=None, connection=None,
                    router=None, result_cls=None, **options):
        args = args if args else ()
        kwargs = kwargs if kwargs else {}
        args = (tuple(args) + tuple(self.args)
                if args and not self.immutable else self.args)
        body = kwargs.pop('body', None) or self.kwargs['body']
        kwargs = dict(self.kwargs['kwargs'], **kwargs)
        body = body.clone(**options)
        app = self._get_app(body)
        tasks = (self.tasks.clone() if isinstance(self.tasks, group)
                 else group(self.tasks, app=app))
        if app.conf.task_always_eager:
            with allow_join_result():
                return self.apply(args, kwargs,
                                  body=body, task_id=task_id, **options)

        merged_options = dict(self.options, **options) if options else self.options
        option_task_id = merged_options.pop("task_id", None)
        if task_id is None:
            task_id = option_task_id

        # chord([A, B, ...], C)
        return self.run(tasks, body, args, task_id=task_id, **merged_options)

    def apply(self, args=None, kwargs=None,
              propagate=True, body=None, **options):
        args = args if args else ()
        kwargs = kwargs if kwargs else {}
        body = self.body if body is None else body
        tasks = (self.tasks.clone() if isinstance(self.tasks, group)
                 else group(self.tasks, app=self.app))
        return body.apply(
            args=(tasks.apply(args, kwargs).get(propagate=propagate),),
        )

    @classmethod
    def _descend(cls, sig_obj):
        # Sometimes serialized signatures might make their way here
        if not isinstance(sig_obj, Signature) and isinstance(sig_obj, dict):
            sig_obj = Signature.from_dict(sig_obj)
        if isinstance(sig_obj, group):
            # Each task in a group counts toward this chord
            subtasks = getattr(sig_obj.tasks, "tasks", sig_obj.tasks)
            return sum(cls._descend(task) for task in subtasks)
        elif isinstance(sig_obj, _chain):
            # The last non-empty element in a chain counts toward this chord
            for child_sig in sig_obj.tasks[-1::-1]:
                child_size = cls._descend(child_sig)
                if child_size > 0:
                    return child_size
            else:
                # We have to just hope this chain is part of some encapsulating
                # signature which is valid and can fire the chord body
                return 0
        elif isinstance(sig_obj, chord):
            # The child chord's body counts toward this chord
            return cls._descend(sig_obj.body)
        elif isinstance(sig_obj, Signature):
            # Each simple signature counts as 1 completion for this chord
            return 1
        # Any other types are assumed to be iterables of simple signatures
        return len(sig_obj)

    def __length_hint__(self):
        tasks = getattr(self.tasks, "tasks", self.tasks)
        return sum(self._descend(task) for task in tasks)

    def run(self, header, body, partial_args, app=None, interval=None,
            countdown=1, max_retries=None, eager=False,
            task_id=None, **options):
        app = app or self._get_app(body)
        group_id = header.options.get('task_id') or uuid()
        root_id = body.options.get('root_id')
        options = dict(self.options, **options) if options else self.options
        if options:
            options.pop('task_id', None)
            body.options.update(options)

        bodyres = body.freeze(task_id, root_id=root_id)

        # Chains should not be passed to the header tasks. See #3771
        options.pop('chain', None)
        # Neither should chords, for deeply nested chords to work
        options.pop('chord', None)
        options.pop('task_id', None)

        header_result_args = header._freeze_group_tasks(group_id=group_id, chord=body, root_id=root_id)

        if header.tasks:
            app.backend.apply_chord(
                header_result_args,
                body,
                interval=interval,
                countdown=countdown,
                max_retries=max_retries,
            )
            header_result = header(*partial_args, task_id=group_id, **options)
        # The execution of a chord body is normally triggered by its header's
        # tasks completing. If the header is empty this will never happen, so
        # we execute the body manually here.
        else:
            body.delay([])
            header_result = self.app.GroupResult(*header_result_args)

        bodyres.parent = header_result
        return bodyres

    def clone(self, *args, **kwargs):
        signature = super().clone(*args, **kwargs)
        # need to make copy of body
        try:
            signature.kwargs['body'] = maybe_signature(
                signature.kwargs['body'], clone=True)
        except (AttributeError, KeyError):
            pass
        return signature

    def link(self, callback):
        self.body.link(callback)
        return callback

    def link_error(self, errback):
        self.body.link_error(errback)
        return errback

    def set_immutable(self, immutable):
        # changes mutability of header only, not callback.
        for task in self.tasks:
            task.set_immutable(immutable)

    def __repr__(self):
        if self.body:
            if isinstance(self.body, _chain):
                return remove_repeating_from_task(
                    self.body.tasks[0]['task'],
                    '%({} | {!r})'.format(
                        self.body.tasks[0].reprcall(self.tasks),
                        chain(self.body.tasks[1:], app=self._app),
                    ),
                )
            return '%' + remove_repeating_from_task(
                self.body['task'], self.body.reprcall(self.tasks))
        return f'<chord without body: {self.tasks!r}>'

    @cached_property
    def app(self):
        return self._get_app(self.body)

    def _get_app(self, body=None):
        app = self._app
        if app is None:
            try:
                tasks = self.tasks.tasks  # is a group
            except AttributeError:
                tasks = self.tasks
            if tasks:
                app = tasks[0]._app
            if app is None and body is not None:
                app = body._app
        return app if app is not None else current_app

    tasks = getitem_property('kwargs.header', 'Tasks in chord header.')
    body = getitem_property('kwargs.body', 'Body task of chord.')


# Add a back-compat alias for the previous `chord` class name which conflicts
# with keyword arguments elsewhere in this file
chord = _chord


def signature(varies, *args, **kwargs):
    """Create new signature.

    - if the first argument is a signature already then it's cloned.
    - if the first argument is a dict, then a Signature version is returned.

    Returns:
        Signature: The resulting signature.
    """
    app = kwargs.get('app')
    if isinstance(varies, dict):
        if isinstance(varies, abstract.CallableSignature):
            return varies.clone()
        return Signature.from_dict(varies, app=app)
    return Signature(varies, *args, **kwargs)


subtask = signature  # XXX compat


def maybe_signature(d, app=None, clone=False):
    """Ensure obj is a signature, or None.

    Arguments:
        d (Optional[Union[abstract.CallableSignature, Mapping]]):
            Signature or dict-serialized signature.
        app (celery.Celery):
            App to bind signature to.
        clone (bool):
            If d' is already a signature, the signature
           will be cloned when this flag is enabled.

    Returns:
        Optional[abstract.CallableSignature]
    """
    if d is not None:
        if isinstance(d, abstract.CallableSignature):
            if clone:
                d = d.clone()
        elif isinstance(d, dict):
            d = signature(d)

        if app is not None:
            d._app = app
    return d


maybe_subtask = maybe_signature  # XXX compat
