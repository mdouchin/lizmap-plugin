import traceback
import json
from pathlib import Path
from configparser import ConfigParser
from typing import Dict

from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsProject,
    QgsMapLayer,
    QgsJsonUtils,
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsDistanceArea,
    QgsFeature,
    QgsFields,
)

from qgis.server import (
    QgsService,
    QgsServerRequest,
    QgsServerResponse,
)

from qgis.PyQt.QtCore import QVariant, QTextCodec

from .core import (
    write_json_response,
    ServiceError,
)

class LizmapServiceError(ServiceError):

    def __init__(self, code: str, msg: str, responseCode: int = 500) -> None:
        super().__init__(code, msg, responseCode)

class LizmapService(QgsService):

    def __init__(self, serverIface: 'QgsServerInterface', debug: bool = False) -> None:
        super().__init__()
        self.server_iface = serverIface
        self.debugMode = debug

    # QgsService inherited

    def name(self) -> str:
        """ Service name
        """
        return 'LIZMAP'

    def version(self) -> str:
        """ Service version
        """
        return "1.0.0"

    def allowMethod(self, method: QgsServerRequest.Method) -> bool:
        """ Check supported HTTP methods
        """
        return method in (
            QgsServerRequest.GetMethod, QgsServerRequest.PostMethod)

    def executeRequest(self, request: QgsServerRequest, response: QgsServerResponse,
                       project: QgsProject) -> None:
        """ Execute a 'LIZMAP' request
        """

        params = request.parameters()

        # noinspection PyBroadException
        try:
            reqparam = params.get('REQUEST', '').upper()

            try:
                data = bytes(request.data()).decode()
            except Exception:
                raise LizmapServiceError(
                    "Bad request error",
                    "Invalid POST DATA for '{}'".format(reqparam),
                    400)

            if reqparam == 'GETSERVERSETTINGS':
                self.getserversettings(params, response, project)
            else:
                raise LizmapServiceError(
                    "Bad request error",
                    "Invalid REQUEST parameter: must be one of EVALUATE, found '{}'".format(reqparam),
                    400)

        except LizmapServiceError as err:
            err.formatResponse(response)
        except Exception:
            QgsMessageLog.logMessage("Unhandled exception:\n%s" % traceback.format_exc(), "lizmap", Qgis.Critical)
            err = LizmapServiceError("Internal server error", "Internal 'lizmap' service error")
            err.formatResponse(response)

    # Lizmap Service request methods
    def getserversettings(self, params: Dict[str, str], response: QgsServerResponse, project: QgsProject) -> None:
        """ Get Lizmap Server settings
        """

        # create the body
        body = {
            'qgis': {},
            'services': [],
            'lizmap': {},
        }

        # QGIS info
        qgis_version_splitted = Qgis.QGIS_VERSION.split('-')
        body['qgis']['version'] = qgis_version_splitted[0]
        body['qgis']['name'] = qgis_version_splitted[1]

        reg = self.server_iface.serviceRegistry()
        services = ['WMS', 'WFS', 'WCS', 'WMTS', 'ATLAS', 'CADASTRE', 'EXPRESSION', 'LIZMAP']
        for s in services:
            if reg.getService(s):
                body['services'].append(s)

        # lizmap plugin metadata.
        metadata_file = Path(__file__).resolve().parent.parent / 'metadata.txt'
        if metadata_file.is_file():
            config = ConfigParser()
            config.read(str(metadata_file))
            body['lizmap']['name'] = config.get('general', 'name')
            body['lizmap']['version'] = config.get('general', 'version')

        write_json_response(body, response)
        return
