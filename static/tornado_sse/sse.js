/**

INSTALLATION:
<script type="text/javascript" src="{{ STATIC_URL }}tornado_sse/jquery.eventsource.js"></script>
<script type="text/javascript" src="{{ STATIC_URL }}tornado_sse/sse.js"></script>

USAGE:
$('body').on('sse.message', function(el, msg){
    console.log(msg);
});

*/

$(function(){
    if($.eventsource) {
        var url = $('body').attr('sse-data');

        $.eventsource({
            label: 'sse',
            url: url,
            dataType: 'json',
            open: function() {
                $('body').trigger('sse.open');
            },
            message: function(msg) {
                var event = 'sse';

                if(msg.type) event += '.' + msg.type;
                else event += '.message';

                console.log(event);
                $('body').trigger(event, msg);
            },
            error: function(msg) {
                $('body').trigger('sse.error', msg);
            }
        });
    }
});
