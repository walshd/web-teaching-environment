/**
 * Generates a new CodeMirror instance for the given textarea.
 * 
 * @param textarea A jQuery object with a single textarea.
 * @returns The new CodeMirror instance
 */
function codemirror_for_textarea(textarea) {
    var options = {
            mode: textarea.data('cm-mimetype'),
            lineNumbers: true,
            indentUnit: 4,
    };
    var override_options = textarea.data('cm-options');
    if(override_options) {
        options = $.extend(options, override_options);
    }
    var cm = CodeMirror.fromTextArea(textarea[0], options);
    cm.setOption("extraKeys", {
        'Tab': function(cm) {
            if(cm.somethingSelected()) {
                cm.indentSelection("add");
                return;
            } else {
                cm.execCommand("insertSoftTab");
            }
        },
        'Shift-Tab': function(cm) {
            cm.indentSelection("subtract");
        }
    });
    return cm;
}
