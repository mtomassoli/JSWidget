// Based on GraphWidget (included in plotly)
// The implementation is not complete, but it's enough for now.

window.genUID = function() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random()*16|0, v = c == 'x' ? r : (r&0x3|0x8);
        return v.toString(16);
    });
};

// The following 8 lines of code were taken from https://github.com/quantopian/qgrid/.
if (IPython.version[0] === '4' && parseInt(IPython.version[2]) >= 2) {
    var path = 'jupyter-js-widgets';
} else {
    var path = 'widgets/js/widget';
    if (IPython.version[0] !== '3') {
        path = 'nbextensions/widgets/' + path;
    }
}

define('JSViewModule', [path, 'plotly'], function (widget, Plotly) {
    var IPYTHON_VERSION = '3';

    if (!('DOMWidgetView' in widget)) {
        // we're in IPython2, things moved a bit from 2 --> 3.
        // construct the expected IPython3 widget API
        widget = {DOMWidgetView: IPython.DOMWidgetView};
    }

    var JSView = widget.DOMWidgetView.extend({
        // Note:
        //   Use "this.send(data)" to send data to the backend.

        render: function() {
            var that = this;
            var graphId = that.model.get('_new_graph_id');

            that.$el.css('width', '100%');
            that.$graph = $([
                             '<div id="' + graphId + '"',
                             'seamless',
                             'style="border: none;"',
                             'width="100%"',
                             'height="600">',
                             '</div>',
                             ].join(' '));
            that.$graph.appendTo(that.$el);
        },

        update: function() {
            var that = this;

            // Listen for messages from the widget in python
            var jmessage = that.model.get('_message');
            var content = JSON.parse(jmessage)[1];
            var graphId = content.graphId;
            var delay = content.delay || 0;

            switch (content.method) {
                case 'noOp':
                    break;

                case 'newPlot':
                    Plotly.newPlot(graphId, content.data, content.layout);
                    break;
            
/*                    // Let's use double buffering to avoid any flickering.

                    var old_graph = $('#' + graphId);
                    var el = old_graph.parent()[0];
                    var width = old_graph.width()
                    var height = old_graph.height()

                    var new_graph = $([
                                       '<div id="' + graphId + '"',
                                       'seamless',
                                       'style="border: none;"',
                                       'width="100%"',
                                       'height="600">',
                                       '</div>',
                                       ].join(' '))[0];

                    // We put new_graph in the DOM but out of sight.
                    new_graph.style.position = 'absolute';
                    new_graph.style.left = '-5000px';
                    el.appendChild(new_graph);

                    function swap_graphs() {
                        if (content.on_completion_id) {
                            that.send({type: 'on_completion',
                                       on_completion_id: content.on_completion_id});
                        }
                        el.removeChild(new_graph);
                        new_graph.style.position = 'static';
                        new_graph.style.left = '0px';
                        old_graph.replaceWith(new_graph);
                    }

                    if (!('width' in content.layout)) {
                        content.layout.width = width;
                    }
                    if (!('height' in content.layout)) {
                        content.layout.height = height;
                    }

                    Plotly.newPlot(new_graph, content.data, content.layout)
                        .then(function () {
                            if (delay == 0) {
                                window.requestAnimationFrame(swap_graphs);
                            } else {
                                window.setTimeout(function () {
                                    window.requestAnimationFrame(swap_graphs);
                                }, delay);
                            }
                        });
                    break;*/

                case 'restyle':
                    if ('indices' in content) {
                        Plotly.restyle(graphId, content.update,
                                       content.indices);
                    } else {
                        Plotly.restyle(graphId, content.update);
                    }
                    break;

                case 'relayout':
                    Plotly.relayout(graphId, content.update);
                    break;

                case 'addTraces':
                    if ('newIndices' in content) {
                        Plotly.addTraces(graphId, content.traces,
                                         content.newIndices);
                    } else {
                        Plotly.addTraces(graphId, content.traces);
                    }
                    break;

                case 'deleteTraces':
                    Plotly.deleteTraces(graphId, content.indices);
                    break;

                case 'moveTraces':
                    if ('newIndices' in content) {
                        Plotly.moveTraces(graphId,
                                          content.currentIndices,
                                          content.newIndices);
                    } else {
                        Plotly.moveTraces(graphId,
                                          content.currentIndices);
                    }
                    break;

                case 'downloadImage':
                    Plotly.downloadImage(graphId,
                                         content.imageProperties);
                    break;

                case 'on':
                    div = document.getElementById(graphId);
                    div.on(content.event_name, function(data) {
                        if (content.drop_full_data) {
                            if ('points' in data) {
                                var num_points = data.points.length;
                                for (var i = 0; i < num_points; i++) {
                                    var point = data.points[i];
                                    if ('data' in point) {
                                        delete point.data;
                                    }
                                    if ('fullData' in point) {
                                        delete point.fullData;
                                    }
                                }
                            }
                        }
                        // send to the python backend
                        that.send({type: 'on', event_name: content.event_name,
                                   'data': data});
                    });

                default:
                    console.error('JSWidget: unrecognized task "' +
                                  content.method + '"');
            }

            return JSView.__super__.update.apply(this);
        },
    });

    return {
        JSView: JSView
    }
});
