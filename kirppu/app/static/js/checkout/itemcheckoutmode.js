// Generated by CoffeeScript 1.7.1
(function() {
  var __hasProp = {}.hasOwnProperty,
    __extends = function(child, parent) { for (var key in parent) { if (__hasProp.call(parent, key)) child[key] = parent[key]; } function ctor() { this.constructor = child; } ctor.prototype = parent.prototype; child.prototype = new ctor(); child.__super__ = parent.prototype; return child; };

  this.ItemCheckoutMode = (function(_super) {
    __extends(ItemCheckoutMode, _super);

    function ItemCheckoutMode() {
      ItemCheckoutMode.__super__.constructor.apply(this, arguments);
      this.receipt = new ItemReceiptTable();
    }

    ItemCheckoutMode.prototype.enter = function() {
      ItemCheckoutMode.__super__.enter.apply(this, arguments);
      return this.cfg.uiRef.body.append(this.receipt.render());
    };

    ItemCheckoutMode.prototype.createRow = function(index, code, name, price, rounded) {
      var price_str, rounded_str, row, x;
      if (price == null) {
        price = null;
      }
      if (rounded == null) {
        rounded = false;
      }
      if (price != null) {
        if (Number.isInteger(price)) {
          price_str = price.formatCents() + "€";
        } else {
          price_str = price;
          rounded = false;
        }
      } else {
        price_str = "";
        rounded = false;
      }
      if (rounded) {
        rounded_str = price.round5().formatCents() + "€";
        price_str = "" + rounded_str + " (" + price_str + ")";
      }
      row = $("<tr>");
      return row.append.apply(row, (function() {
        var _i, _len, _ref, _results;
        _ref = [index, code, name, price_str];
        _results = [];
        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
          x = _ref[_i];
          _results.push($("<td>").text(x));
        }
        return _results;
      })());
    };

    return ItemCheckoutMode;

  })(CheckoutMode);

  Number.prototype.round5 = function() {
    var modulo;
    modulo = this % 5;
    if (modulo >= 2.5) {
      return this + (5 - modulo);
    } else {
      return this - modulo;
    }
  };

}).call(this);
