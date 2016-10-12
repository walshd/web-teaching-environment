(function($) {
    /**
     * The sendBeacon jQuery function handles sending a navigator.sendBeacon request.
     */
    $.sendBeacon = function(url, data) {
        if(navigator.sendBeacon === undefined) {
            $.ajax(url, {
                method: 'POST',
                data: data,
                async: false
            });
        } else {
            try {
                var fd = new FormData();
                for(var key in data) {
                    fd.append(key, data[key]);
                }
                navigator.sendBeacon(url, fd);
            } catch(err) {}
        }
    };
}(jQuery));
