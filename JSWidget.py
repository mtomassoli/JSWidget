# Based on GraphWidget (included in plotly)
# The implementation is not complete, but it's enough for now.

import json
from collections import deque
from pkg_resources import resource_string

try:
    import ipywidgets as widgets
except ImportError:
    from IPython.html import widgets

try:
    from traitlets import Unicode
except ImportError:
    from IPython.utils.traitlets import Unicode

from IPython.display import Javascript, display, HTML

from plotly import utils, tools

from plotly.offline import init_notebook_mode

import uuid
import time


class JSWidget(widgets.DOMWidget):
    """
    A widget for plotting and updating graphs OFFLINE in IPython Notebooks.
    """
    _view_name = Unicode('JSView').tag(sync=True)
    _view_module = Unicode('JSViewModule').tag(sync=True)
    _message = Unicode().tag(sync=True)
    _new_graph_id = Unicode().tag(sync=True)
    _uid_dict = {}              # used for on_completion

    # Inject JSWidget.js.
    js_widget_code = resource_string(__name__, 'JSWidget.js').decode('utf-8')
    display(Javascript(js_widget_code))

    # Inject plotly.js (included in plotly).
    init_notebook_mode(connected=False)

    def __init__(self, initial_height=None, initial_width=None, **kwargs):
        super(JSWidget, self).__init__(**kwargs)

        self._switch = False
        self.on_msg(self._handle_msg)

        id = str(uuid.uuid4())
        self._graph_id = id
        self._new_graph_id = id         # sends id to JS

        self._cur_height = initial_height or 600
        self._cur_width = initial_width or '100%'

        self._event_handlers = {}
        self._unsent_msgs = deque()

        self._displayed = False

    def _ipython_display_(self, **kwargs):
        if self._displayed:
            print("You can't display the same widget more than once!")
        else:
            super(JSWidget, self)._ipython_display_(**kwargs)
            self._displayed = True

            # We can finally send the unsent messages.
            while self._unsent_msgs:
                msg = self._unsent_msgs.popleft()
                self._send_message(msg)

    def _send_message(self, message):
        if self._displayed:
            self._message = json.dumps([self._switch, message],
                                       cls=utils.PlotlyJSONEncoder)
            self._switch = not self._switch
        else:
            # We can't send the message until the widget has been displayed.
            self._unsent_msgs.append(message)

    def _handle_msg(self, message):        # ouch: don't change this name!
        content = message['content']['data']['content']
        ctype = content['type']
        if ctype == 'on':
            self._event_handlers[content.event_name]()
        elif ctype == 'on_completion':
            callback = self._uid_dict.pop(content['on_completion_id'], False)
            if callback:
                callback()
        else:
            raise ValueError('Unrecognized ctype: ' + ctype)

    def on(self, event_name, handler, drop_trace_data=True, remove=False):
        """
        See https://plot.ly/javascript/plotlyjs-events/

        handler will be passed a structure data which contains several
        information relative to the event.
        If `drop_trace_data` is True, then all the fields `data` and
        `full_data`, if present, will be dropped. This is useful for efficiency
        reasons.
        """
        dispatcher = self._event_handlers.get(event_name)
        if remove:
            if not dispatcher or event_name not in dispatcher.callbacks:
                raise Exception('tried to remove a handler never registered')
            dispatcher.register_callback(handler, remove=True)
        else:
            if dispatcher:
                dispatcher.register_callback(handler)
            else:
                dispatcher = widgets.CallbackDispatcher()
                self._event_handlers[event_name] = dispatcher

                # The first registration must be done on the frontend as well.
                message = {
                    'method': 'on',
                    'event_name': event_name,
                    'drop_trace_data': drop_trace_data,
                    'graphId': self._graph_id
                }
                self._send_message(message)

    def clear_plot(self):
        """
        Note:
            This calls newPlot which unregisters all your event handlers.
        """
        message = {
            'method': 'newPlot',
            'data': [],
            'layout': {},
            'graphId': self._graph_id,
            'delay': 0,
        }
        self._send_message(message)

        # newPlot unregisters all the event handlers.
        self._event_handlers.clear()

    def new_plot(self, figure_or_data, validate=True, on_completion=None,
                 delay=0):
        """
        See https://plot.ly/javascript/plotlyjs-function-reference/
        Note that JS functions are in camelCase.

        The only difference is that you need to pass a figure if you want to
        specify a layout.

        Note:
            newPlot unregisters all your event handlers.
        """
        on_completion_id = None
        if on_completion:
            on_completion_id = str(uuid.uuid4())
            self._uid_dict[on_completion_id] = on_completion

        figure = tools.return_figure_from_figure_or_data(figure_or_data,
                                                         validate)
        message = {
            'method': 'newPlot',
            'data': figure.get('data', []),
            'layout': figure.get('layout', {}),
            'graphId': self._graph_id,
            'delay': delay,
            'on_completion_id': on_completion_id,
        }
        self._send_message(message)

        # newPlot unregisters all the event handlers.
        self._event_handlers.clear()

    def restyle(self, update, indices=None):
        """
        See https://plot.ly/javascript/plotlyjs-function-reference/
        Note that JS functions are in camelCase.
        """
        message = {
            'method': 'restyle',
            'update': update,
            'graphId': self._graph_id
        }
        if indices:
            message['indices'] = indices
        self._send_message(message)

    def relayout(self, layout):
        """
        See https://plot.ly/javascript/plotlyjs-function-reference/
        Note that JS functions are in camelCase.
        """
        message = {
            'method': 'relayout',
            'update': layout,
            'graphId': self._graph_id
        }
        self._send_message(message)

    def add_traces(self, traces, new_indices=None):
        """
        See https://plot.ly/javascript/plotlyjs-function-reference/
        Note that JS functions are in camelCase.
        """
        message = {
            'method': 'addTraces',
            'traces': traces,
            'graphId': self._graph_id
        }
        if new_indices:
            message['newIndices'] = new_indices
        self._send_message(message)

    def delete_traces(self, indices):
        """
        See https://plot.ly/javascript/plotlyjs-function-reference/
        Note that JS functions are in camelCase.
        """
        message = {
            'method': 'deleteTraces',
            'indices': indices,
            'graphId': self._graph_id
        }
        self._send_message(message)

    def move_traces(self, current_indices, new_indices=None):
        """
        See https://plot.ly/javascript/plotlyjs-function-reference/
        Note that JS functions are in camelCase.
        """
        message = {
            'method': 'moveTraces',
            'currentIndices': current_indices,
            'graphId': self._graph_id
        }
        if new_indices:
            message['newIndices'] = new_indices
        self._send_message(message)

    def download_image(self, format, width, height, filename):
        """
        See https://plot.ly/javascript/plotlyjs-function-reference/
        Note that JS functions are in camelCase.
        """
        message = {
            'method': 'downloadImage',
            'imageProperties': dict(format=format,
                                    width=width,
                                    height=height,
                                    filename=filename)
        }
        self._send_message(message)
