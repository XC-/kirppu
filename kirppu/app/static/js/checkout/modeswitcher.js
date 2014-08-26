// Generated by CoffeeScript 1.7.1
(function() {
  var setClass,
    __bind = function(fn, me){ return function(){ return fn.apply(me, arguments); }; };

  setClass = function(element, cls, enabled) {
    if (element.hasClass(cls) !== enabled) {
      if (enabled) {
        element.addClass(cls);
      } else {
        element.removeClass(cls);
      }
    }
    return element;
  };

  this.ModeSwitcher = (function() {
    ModeSwitcher.entryPoints = {};

    ModeSwitcher.registerEntryPoint = function(name, mode) {
      if (name in this.entryPoints) {
        return console.error("Name '" + name + "' was already registered for '" + this.entryPoints[name].name + "' while registering '" + mode.name + "'.");
      } else {
        return this.entryPoints[name] = mode;
      }
    };

    function ModeSwitcher(config) {
      this._onFormSubmit = __bind(this._onFormSubmit, this);
      this.cfg = config ? config : CheckoutConfig;
      this._currentMode = null;
      this._bindMenu(ModeSwitcher.entryPoints);
      this._bindForm();
    }

    ModeSwitcher.prototype.startDefault = function() {
      return this.switchTo(ModeSwitcher.entryPoints["counter_validation"]);
    };

    ModeSwitcher.prototype.switchTo = function(mode) {
      if (this._currentMode != null) {
        this._currentMode.exit();
      }
      this.setMenuEnabled(true);
      this._currentMode = new mode(this, this.cfg);
      this.cfg.uiRef.stateText.text(this._currentMode.title());
      this.cfg.uiRef.subtitleText.text(this._currentMode.subtitle() || "");
      return this._currentMode.enter();
    };

    ModeSwitcher.prototype._bindForm = function() {
      var form;
      form = this.cfg.uiRef.codeForm;
      form.off("submit");
      return form.submit(this._onFormSubmit);
    };

    ModeSwitcher.prototype._onFormSubmit = function(event) {
      var a, actions, handler, input, matching, prefix, _ref;
      event.preventDefault();
      input = this.cfg.uiRef.codeInput.val();
      actions = this._currentMode.actions();
      matching = (function() {
        var _i, _len, _results;
        _results = [];
        for (_i = 0, _len = actions.length; _i < _len; _i++) {
          a = actions[_i];
          if (input.indexOf(a[0]) === 0) {
            _results.push(a);
          }
        }
        return _results;
      })();
      matching = matching.sort(function(a, b) {
        return b[0].length - a[0].length;
      });
      if (matching[0] != null) {
        _ref = matching[0], prefix = _ref[0], handler = _ref[1];
        handler(input.slice(prefix.length), prefix);
        return this.cfg.uiRef.codeInput.val("");
      } else {
        return console.error("Input not accepted: '" + input + "'.");
      }
    };

    ModeSwitcher.prototype._bindMenu = function(entryPoints) {
      var entryPoint, entryPointName, item, itemDom, items, menu, _i, _len;
      menu = this.cfg.uiRef.modeMenu;
      items = menu.find("[data-entrypoint]");
      for (_i = 0, _len = items.length; _i < _len; _i++) {
        itemDom = items[_i];
        item = $(itemDom);
        entryPointName = item.attr("data-entrypoint");
        if (entryPointName in entryPoints) {
          entryPoint = entryPoints[entryPointName];
          (function(this_, ep) {
            return item.click(function() {
              console.log("Changing mode from menu to " + ep.name);
              return this_.switchTo(ep);
            });
          })(this, entryPoint);
        } else {
          console.warn("Entry point '" + entryPointName + "' could not be found from registered entry points. Source:");
          console.log(itemDom);
        }
      }
    };

    ModeSwitcher.prototype.setMenuEnabled = function(enabled) {
      var menu;
      menu = this.cfg.uiRef.modeMenu;
      setClass(menu, "disabled", !enabled);
      return setClass(menu.find("a:first"), "disabled", !enabled);
    };

    return ModeSwitcher;

  })();

}).call(this);