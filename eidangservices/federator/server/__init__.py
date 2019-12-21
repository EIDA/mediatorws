# -*- coding: utf-8 -*-

import datetime
import uuid

from flask import Flask, make_response, g
from flask_cors import CORS
from flask_redis import FlaskRedis

# from werkzeug.contrib.profiler import ProfilerMiddleware

from eidangservices import settings
from eidangservices.federator import __version__
from eidangservices.federator.server.stats import ResponseCodeStats
from eidangservices.federator.server.cache import Cache
from eidangservices.utils import httperrors
from eidangservices.utils.error import Error
from eidangservices.utils.fdsnws import (register_parser_errorhandler,
                                         register_keywordparser_errorhandler)


redis_client = FlaskRedis()

response_code_stats = ResponseCodeStats(redis=redis_client)

cache = Cache()


def create_app(config_dict={}, service_version=__version__):
    """
    Factory function for Flask application.

    :param config_dict: flask configuration object
    :type config_dict: :py:class:`flask.Config`
    :param str service_version: Version string
    """
    # prevent from errors due to circular dependencies
    # XXX(damb): Consider refactoring
    from eidangservices.federator.server.misc import Context
    app = Flask(__name__)
    app.config.update(config_dict)
    # allows CORS for all domains for all routes
    CORS(app)

    redis_client.init_app(app, socket_timeout=5)
    # configure response code time series
    response_code_stats.kwargs_series = {
        'window_size': config_dict['FED_CRETRY_BUDGET_WINDOW_SIZE'],
        'ttl': config_dict['FED_CRETRY_BUDGET_TTL'],
    }
    # configure cache
    cache.init_cache(config=config_dict)

    # app.config['PROFILE'] = True
    # app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[10])

    # TODO(damb): move webservice error handling to eidangservices.utils
    @app.before_request
    def before_request():
        g.request_start_time = datetime.datetime.utcnow()
        g.request_id = uuid.uuid4()
        g.ctx = Context(ctx=g.request_id)
        g.ctx.acquire()

    @app.teardown_request
    def teardown_request(exception):
        try:
            g.ctx.release()
        except Error:
            pass

    def register_error(err):
        @app.errorhandler(err)
        def handle_error(error):
            return make_response(
                error.description, error.code,
                {'Content-Type': '{}; {}'.format(settings.ERROR_MIMETYPE,
                                                 settings.CHARSET_TEXT)})

    errors_to_register = (
        httperrors.NoDataError,
        httperrors.BadRequestError,
        httperrors.RequestTooLargeError,
        httperrors.RequestURITooLargeError,
        httperrors.InternalServerError,
        httperrors.TemporarilyUnavailableError)

    for err in errors_to_register:
        register_error(err)

    register_parser_errorhandler(service_version=service_version)
    register_keywordparser_errorhandler(service_version=service_version)

    return app
