from flask_restful import Resource
from pygal.style import Style
from .. import ctx
import pygal
import timeago
from math import ceil


class HistoryGraph(Resource):
    def get(self, start_index):
        try:
            custom_style = Style(background='transparent',
                                 plot_background='transparent',
                                 foreground='#6c757d',
                                 foreground_strong='#6c757d',
                                 foreground_subtle='#6c757d',
                                 opacity='0.1',
                                 opacity_hover='0.2',
                                 transition='0ms',
                                 colors=('#749363', '#007acc'), )

            graph = pygal.Line(stroke_style={'width': 0.4},
                               show_legend=False,
                               fill=True,
                               style=custom_style,
                               disable_xml_declaration=True)

            start_index = int(start_index)
            total_entries = len(ctx.history.instance_history)
            detail_level = 500
            zoom_increment_factor = 2
            interval = max(1, ceil((total_entries - start_index) / detail_level))
            instance_count = [history['time'] for history in ctx.history.instance_history[start_index::interval]]

            if len(instance_count) > 0:
                graph.x_labels = [timeago.format(instance_count[0])]

            instance_counts = [{'value': int(history['count']), 'label': timeago.format(history['time'])} for history in
                               ctx.history.instance_history[start_index::interval]]
            client_counts = [{'value': int(history['count']), 'label': timeago.format(history['time'])} for history in
                             ctx.history.client_history[start_index::interval]]
            server_counts = [{'value': int(history['count']), 'label': timeago.format(history['time'])} for history in
                             ctx.history.server_history[start_index::interval]]
            previous_zoom_point = 0 if start_index == total_entries else max(0, start_index - ceil(
                (len(ctx.history.instance_history) - start_index)))
            next_zoom_point = start_index + ceil(
                (len(ctx.history.instance_history) - start_index) / zoom_increment_factor)

            graph.add('Client Count', client_counts)
            graph.add('Instance Count', instance_counts)
            return {'message': graph.render().replace("<title>Pygal</title>", ""),
                    'instance_count': 0 if len(instance_counts) == 0 else instance_counts[-1],
                    'client_count': 0 if len(client_counts) == 0 else client_counts[-1],
                    'server_count': 0 if len(server_counts) == 0 else server_counts[-1],
                    'next_zoom_point': next_zoom_point,
                    'previous_zoom_point': previous_zoom_point
                    }, 200
        except Exception as e:
            return {'message': str(e)}, 500
