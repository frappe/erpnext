(function() {
  var CheckGrid, content_items, cx;
  var __bind = function(fn, me){ return function(){ return fn.apply(me, arguments); }; };
  content_items = ['Sales', 'Expenses', 'Bank Balance', 'Activity'];
  CheckGrid = (function() {
    function CheckGrid(args) {
      this.args = args;
      this.set = __bind(this.set, this);
      this.get = __bind(this.get, this);
      $.extend(this, args);
      this.wrapper = $a(this.parent, 'div', 'check-grid round');
      this.render();
    }
    CheckGrid.prototype.render = function() {
      var i, _ref;
      $a(this.wrapper, 'h3', 'check-grid-title', null, this.label);
      if (this.description) {
        $a(this.wrapper, 'div', 'help-box', null, this.description);
      }
      this.tab = make_table(this.wrapper, this.items.length + 1, this.columns.length, '100%', this.widths);
      this.checks = {};
      for (i = 0, _ref = this.columns.length - 1; 0 <= _ref ? i <= _ref : i >= _ref; 0 <= _ref ? i++ : i--) {
        $($td(this.tab, 0, i)).addClass('check-grid-head gradient').html(this.columns[i]);
      }
      return this.render_rows();
    };
    CheckGrid.prototype.render_rows = function() {
      var c, check, i, _ref, _results;
      _results = [];
      for (i = 0, _ref = this.items.length - 1; 0 <= _ref ? i <= _ref : i >= _ref; 0 <= _ref ? i++ : i--) {
        $td(this.tab, i + 1, 0).innerHTML = this.items[i];
        this.checks[this.items[i]] = {};
        _results.push((function() {
          var _ref2, _results2;
          _results2 = [];
          for (c = 1, _ref2 = this.columns.length - 1; 1 <= _ref2 ? c <= _ref2 : c >= _ref2; 1 <= _ref2 ? c++ : c--) {
            check = $a_input($td(this.tab, i + 1, c), 'checkbox');
            check.item = this.items[i];
            check.column = this.columns[c];
            _results2.push(this.checks[this.items[i]][this.columns[c]] = check);
          }
          return _results2;
        }).call(this));
      }
      return _results;
    };
    CheckGrid.prototype.get = function() {
      var check, column, item, val, _i, _j, _len, _len2, _name, _ref, _ref2;
      val = {};
      _ref = keys(this.checks);
      for (_i = 0, _len = _ref.length; _i < _len; _i++) {
        item = _ref[_i];
        _ref2 = keys(this.checks[item]);
        for (_j = 0, _len2 = _ref2.length; _j < _len2; _j++) {
          column = _ref2[_j];
          check = this.checks[item][column];
          val[_name = check.item] || (val[_name] = {});
          val[check.item][check.column] = check.checked ? 1 : 0;
        }
      }
      return val;
    };
    CheckGrid.prototype.set = function(val) {
      var column, item, _i, _j, _len, _len2, _ref, _ref2;
      _ref = keys(this.checks);
      for (_i = 0, _len = _ref.length; _i < _len; _i++) {
        item = _ref[_i];
        _ref2 = keys(this.checks[item]);
        for (_j = 0, _len2 = _ref2.length; _j < _len2; _j++) {
          column = _ref2[_j];
          if (val[item][column]) {
            this.checks[item][column].checked = val[item][column];
          }
        }
      }
    };
    return CheckGrid;
  })();
  cx = cur_frm.cscript;
  cx.onload = function(doc, dt, dn) {
    cx.content_grid = new CheckGrid({
      parent: cur_frm.fields_dict.Body.wrapper,
      label: 'Email Settings',
      items: content_items,
      columns: ['Item', 'Daily', 'Weekly'],
      widths: ['60%', '20%', '20%'],
      description: 'Select items to be compiled for Email Digest'
    });
    cx.email_grid = new CheckGrid({
      parent: cur_frm.fields_dict.Body.wrapper,
      label: 'Send To',
      items: ['test1@erpnext', 'test2@erpnext'],
      columns: ['Email', 'Daily', 'Weekly'],
      widths: ['60%', '20%', '20%'],
      description: 'Select who gets daily and weekly mails'
    });
    if (doc.content_config) {
      cx.content_grid.set(JSON.parse(doc.content_config));
    }
    if (doc.email_config) {
      cx.email_grid.set(JSON.parse(doc.email_config));
    }
  };
  cx.validate = function(doc, dt, dn) {
    doc.content_config = JSON.stringify(cx.content_grid.get());
    return doc.email_config = JSON.stringify(cx.email_grid.get());
  };
}).call(this);
