(function() {
  var CheckGrid, content_items, cx, freq;
  var __bind = function(fn, me){ return function(){ return fn.apply(me, arguments); }; };
  content_items = ['Sales', 'Expenses', 'Bank Balance', 'Activity'];
  freq = ['Daily', 'Weekly'];
  CheckGrid = (function() {
    function CheckGrid(parent, label, items, columns) {
      var c, check, i, _ref, _ref2, _ref3;
      this.parent = parent;
      this.label = label;
      this.items = items;
      this.columns = columns;
      this.set = __bind(this.set, this);
      this.get = __bind(this.get, this);
      this.tab = make_table(this.parent, this.items.length + 1, this.columns.length + 1, '80%');
      this.checks = {};
      for (i = 0, _ref = this.columns.length - 1; 0 <= _ref ? i <= _ref : i >= _ref; 0 <= _ref ? i++ : i--) {
        $td(this.tab, 0, i + 1).innerHTML = this.columns[i];
      }
      for (i = 0, _ref2 = this.items.length - 1; 0 <= _ref2 ? i <= _ref2 : i >= _ref2; 0 <= _ref2 ? i++ : i--) {
        $td(this.tab, i + 1, 0).innerHTML = this.items[i];
        this.checks[this.items[i]] = {};
        for (c = 0, _ref3 = this.columns.length - 1; 0 <= _ref3 ? c <= _ref3 : c >= _ref3; 0 <= _ref3 ? c++ : c--) {
          check = $a_input($td(this.tab, i + 1, c + 1), 'checkbox');
          check.item = this.items[i];
          check.column = this.columns[c];
          this.checks[this.items[i]][this.columns[c]] = check;
        }
      }
    }
    CheckGrid.prototype.get = function() {
      var check, column, item, val, _i, _j, _len, _len2, _ref, _ref2;
      val = {};
      _ref = keys(this.checks);
      for (_i = 0, _len = _ref.length; _i < _len; _i++) {
        item = _ref[_i];
        _ref2 = keys(this.checks[item]);
        for (_j = 0, _len2 = _ref2.length; _j < _len2; _j++) {
          column = _ref2[_j];
          check = this.checks[item][column];
          if (!val[check.item]) {
            val[check.item] = {};
          }
          val[check.item][check.column] = check.checked ? 1 : 0;
        }
      }
      return val;
    };
    CheckGrid.prototype.set = function(val) {
      var check, column, item, _i, _len, _ref, _results;
      _ref = keys(this.checks);
      _results = [];
      for (_i = 0, _len = _ref.length; _i < _len; _i++) {
        item = _ref[_i];
        _results.push((function() {
          var _j, _len2, _ref2, _results2;
          _ref2 = keys(this.checks[item]);
          _results2 = [];
          for (_j = 0, _len2 = _ref2.length; _j < _len2; _j++) {
            column = _ref2[_j];
            check = this.checks[item][column];
            _results2.push(check.checked = val[check.item][check.row]);
          }
          return _results2;
        }).call(this));
      }
      return _results;
    };
    return CheckGrid;
  })();
  cx = cur_frm.cscript;
  cx.onload = function(doc, dt, dn) {
    cx.content_grid = new CheckGrid(cur_frm.fields_dict.Body.wrapper, 'Email Settings', content_items, freq);
    return cx.email_grid = new CheckGrid(cur_frm.fields_dict.Body.wrapper, 'Send To', ['test1@erpnext', 'test2@erpnext'], freq);
  };
  cx.validate = function(doc, dt, dn) {
    doc.content_config = JSON.stringify(cx.content_grid.get());
    return doc.email_config = JSON.stringify(cx.email_grid.get());
  };
}).call(this);
