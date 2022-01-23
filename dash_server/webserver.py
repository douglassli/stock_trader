from dash import dcc, html, Dash
from dash.dependencies import Input, Output
from datetime import datetime
from numpy import nan
import plotly.graph_objects as go
from utils.utils import get_queue_items
from utils.constants import TRACE_MODES


class TradeMonitorWebServer:
    def __init__(self, update_queue):
        # {
        #   symbol: '',
        #   timestamp: '',
        #   trace_points: {
        #     trace_name: {point: '', trace_type: ''},
        #     ...
        #   }
        # }
        self.update_queue = update_queue
        # {
        #   symbol: {
        #     timestamps: []
        #     traces: {
        #       trace_name: {
        #         trace_type: 'vwma'/'cost'/'psar'/etc,
        #         data: []
        #       }
        #     }
        #   }
        # }
        self.stock_data = {}
        self.buy_sell_points = {}

        self.app = Dash(__name__)
        self.app.layout = html.Div(children=[
            html.H1(children='Stock Trader Bot Monitor'),
            dcc.Interval(
                id='update_interval',
                interval=10 * 1000,  # Check for updates every 10 seconds
                n_intervals=0
            ),
            html.Div(id='graphs', children=[])
        ])

        @self.app.callback(Output('graphs', 'children'), Input('update_interval', 'n_intervals'))
        def _(n):
            self.pull_new_data()
            return self.update_graph_live(n)

    def pull_new_data(self):
        for update in get_queue_items(self.update_queue):
            symbol = update['symbol']
            if symbol not in self.stock_data:
                self.stock_data[symbol] = {
                    'timestamps': [],
                    'traces': {}
                }

            self.stock_data[symbol]['timestamps'].append(update['timestamp'])

            for trace_name, trace_data in update['trace_points'].items():
                if trace_name not in self.stock_data[symbol]['traces']:
                    self.stock_data[symbol]['traces'][trace_name] = {
                        'trace_type': trace_data['trace_type'],
                        'data': []
                    }

                self.stock_data[symbol]['traces'][trace_name]['data'].append(trace_data['point'])

    def update_graph_live(self, num_intervals):
        out_figures = []
        for symbol, data in self.stock_data.items():
            figure = self.build_figure(symbol, data)
            out_figures.append(
                dcc.Graph(
                    id=f"graph_{symbol}",
                    figure=figure
                )
            )
        return out_figures

    def build_figure(self, symbol, data):
        font = go.layout.title.Font(size=36)
        title = go.layout.Title(text=symbol, xanchor="center", xref="paper", x=0.5, font=font)
        layout = go.Layout(title=title, titlefont=font)
        fig = go.Figure(layout=layout)

        for trace_name, trace in data['traces'].items():
            fig.add_trace(go.Scatter(
                x=data['timestamps'],
                y=trace['data'],
                mode=TRACE_MODES[trace['trace_type']],
                name=trace_name)
            )

        fig.update_traces(marker_size=2)

        now = datetime.utcnow()  # TODO terrible
        # Not my bug https://github.com/plotly/plotly.py/issues/3065
        fig.add_vline(
            x=datetime(year=now.year, month=now.month, day=now.day, hour=14, minute=30).timestamp() * 1000,
            annotation_text="open"
        )
        fig.add_vline(
            x=datetime(year=now.year, month=now.month, day=now.day,  hour=21).timestamp() * 1000,
            annotation_text="close"
        )

        return fig

    def start_server(self):
        self.app.run_server()


def start_webserver_process(update_queue):
    server = TradeMonitorWebServer(update_queue)
    server.start_server()
