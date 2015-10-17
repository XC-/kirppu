module.exports.css = {
    'general': {
        "source_filenames": [
            "css/general.css",
            "../node_modules/bootstrap/dist/css/bootstrap.css",
            "../node_modules/bootstrap/dist/css/bootstrap-theme.css",
        ],
        "output_filename": "general.css",
    },
    'vendor': {
        "source_filenames": [
            "css/app.css",
        ],
        "output_filename": "vendor.css",
    },
    'price_tags': {
        "source_filenames": [
            "css/price_tags.css",
        ],
        "output_filename": "price_tags.css",
    },
    'boxes': {
        "source_filenames": [
            "css/boxes.css",
        ],
        "output_filename": "boxes.css",
    },
    'checkout': {
        "source_filenames": [
            "css/checkout.css",
        ],
        "output_filename": "checkout.css",
    }
};

module.exports.js = {
    'general': {
        "source_filenames": [
            "js/gettext_shim.js",
            "../node_modules/jquery/dist/jquery.js",
            "../node_modules/bootstrap/dist/js/bootstrap.js",
            "js/csrf.coffee",
        ],
        "output_filename": "general.js",
        "compress": true,
    },
    'price_tags': {
        "source_filenames": [
            "js/number_test.coffee",
            "js/price_tags.coffee",
        ],
        "output_filename": "price_tags.js",
        "compress": true,
    },
    'boxes': {
        "source_filenames": [
            "js/number_test.coffee",
            "js/boxes.coffee",
        ],
        "output_filename": "boxes.js",
        "compress": true,
    },
    'checkout': {
        "source_filenames": [
            "js/checkout/util.coffee",
            "js/checkout/checkout.coffee",
            "js/checkout/datetime_formatter.coffee",
            "js/checkout/dialog.coffee",

            "js/checkout/resulttable.coffee",
            "js/checkout/itemreceipttable.coffee",
            "js/checkout/itemreporttable.coffee",
            "js/overseer/item_find_list.coffee",
            "js/overseer/item_search_form.coffee",
            "js/overseer/item_edit_dialog.coffee",
            "js/checkout/vendorlist.coffee",
            "js/checkout/vendorinfo.coffee",
            "js/checkout/receiptsum.coffee",
            "js/checkout/printreceipttable.coffee",

            "js/checkout/modeswitcher.coffee",
            "js/checkout/checkoutmode.coffee",
            "js/checkout/itemcheckoutmode.coffee",

            "js/checkout/countervalidationmode.coffee",
            "js/checkout/clerkloginmode.coffee",
            "js/checkout/itemcheckinmode.coffee",
            "js/overseer/item_find_mode.coffee",
            "js/checkout/vendorcheckoutmode.coffee",
            "js/checkout/countermode.coffee",
            "js/checkout/receiptprintmode.coffee",
            "js/checkout/vendorcompensation.coffee",
            "js/checkout/vendorreport.coffee",
            "js/checkout/vendorfindmode.coffee",

            "js/number_test.coffee",

            "js/overseer/lost_and_found.coffee",
            "js/overseer/lost_and_found_table.coffee",

            "js/overseer/receipt_list_mode.coffee",
            "js/overseer/receipt_list.coffee",

            "js/stats.coffee",
        ],
        "output_filename": "checkout.js",
    },
    'checkout_compressed': {
        "source_filenames": [
            "js/jquery.cookie-1.4.1-0.js",
            "js/moment.js",
            "js/moment.fi.js",
        ],
        "output_filename": "checkout_comp.js",
        "compress": true
    },
    'jeditable': {
        "source_filenames": [
            "js/jquery.jeditable.js",
        ],
        "output_filename": "jeditable.js",
        "compress": true,
    },
    'command_list': {
        "source_filenames": [
            "js/commands.coffee"
        ],
        "output_filename": "commands.js"
    },
    'dygraph': {
        "source_filenames": [
            "js/dygraph-combined-dev.js"
        ],
        "output_filename": "dygraph-combined.js",
        "compress": true
    }
};
module.exports.static = {
    "general": {
        "source_filenames": [
            "audio/bleep.mp3",
            "audio/error-buzzer.mp3",
            "img/roller.gif"
        ]
    },
    "bootstrap": {
        "dest": "fonts",
        "source_filenames": [
            "../node_modules/bootstrap/fonts/glyphicons-halflings-regular.eot",
            "../node_modules/bootstrap/fonts/glyphicons-halflings-regular.ttf",
            "../node_modules/bootstrap/fonts/glyphicons-halflings-regular.svg",
            "../node_modules/bootstrap/fonts/glyphicons-halflings-regular.woff",
            "../node_modules/bootstrap/fonts/glyphicons-halflings-regular.woff2"
        ]
    }
};
