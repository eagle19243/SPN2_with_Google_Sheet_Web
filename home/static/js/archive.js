window.onload = function() {
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);

                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }

        return cookieValue;
    }

    $.ajaxSetup({
         beforeSend: function(xhr, settings) {
             if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
                 xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
             }
         }
    });

    $("#btn_archive").click(function() {
        $(".progress").asProgress("go", "0%");
        $(".progress").show();
        $('.progress-status').html('Processing');
        $('.progress-status').show();

        $.ajax({
            url: "/archive/",
            method: "POST",
            data: {
                    "access_key" : $("#access_key").val(),
                    "secret_key" : $("#secret_key").val(),
                    "google_sheet_url" : $("#google_sheet_url").val()
            },
            success: function(res){
                if (res.success) {
                    var timer = setInterval(function(){
                        $.ajax({
                            url: "/get_progress",
                            method: "GET",
                            data: {job: res.job},
                            success: function(res) {
                                res = JSON.parse(res);

                                if (res == "SUCCESS") {
                                    $(".progress").asProgress("go", "100%");
                                    $('.progress-status').html('Done');
                                    $('.progress-url').html("");
                                    timer.clearInterval();
                                } else {
                                    $(".progress").asProgress("go", res.current + "%");
                                    $('.progress-status').html('Processing');

                                    if (res.url) {
                                        $('.progress-url').html(res.url);
                                    }
                                }
                            }
                        });
                    }, 1000);
                } else {
                    $('.status').html('Failed: ' + res.message);
                }
            }
        });
    });
}
