import os
import math
from enum import Enum
from geographiclib.geodesic import Geodesic

from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.core import *
from qgis.gui import *


class OverlayPC7Layer(QgsPluginLayer):

    def __init__(self, layer_name):
        QgsPluginLayer.__init__(self, self.pluginLayerType(), layer_name)

        self.setValid(True)
        self.center = QgsPointXY()
        self.azimut = None
        self.azimutLeftFL = None  # Azimut left flight line
        self.azimutRightFL = None  # Azimut right flight line
        self.color = Qt.red
        self.lineWidth = 3
        self.transparency = 0
        self.layer_name = layer_name

    @classmethod
    def pluginLayerType(self):
        return "overlaypc7"

    def setTransformContext(self, context):
        pass

    def setup(self, center, crs, azimut, azimutLeftFL, azimutRightFL):
        self.center = center
        self.azimut = azimut
        self.azimutLeftFL = azimutLeftFL
        self.azimutRightFL = azimutRightFL

        self.setCrs(crs, False)

    def writeSymbology(self, node, doc, errorMsg):
        return True

    def readSymbology(self, node, errorMsg):
        return True

    def createMapRenderer(self, rendererContext):
        return Renderer(self, rendererContext)

    def extent(self):
        radius = 230
        radius *= QgsUnitTypes.fromUnitToUnitFactor(
            QgsUnitTypes.DistanceMeters, self.crs().mapUnits())

        return QgsRectangle(self.center.x() - radius, self.center.y() - radius,
                            self.center.x() + radius, self.center.y() + radius)

    def azimutToRadiant(self, azimut):
        return (azimut / 180) * math.pi

    def getCenter(self):
        return self.center

    def getAzimut(self, radiant=False):
        if radiant:
            return self.azimutToRadiant(self.azimut)
        return self.azimut

    def getAzimutLeftFL(self, radiant=False):
        if radiant:
            return self.azimutToRadiant(self.azimutLeftFL)
        return self.azimutLeftFL

    def getAzimutRightFL(self, radiant=False):
        if radiant:
            return self.azimutToRadiant(self.azimutRightFL)
        return self.azimutRightFL

    def getColor(self):
        return self.color

    def getLineWidth(self):
        return self.lineWidth

    def setColor(self, color):
        self.color = color

    def setLineWidth(self, lineWidth):
        self.lineWidth = lineWidth

    def readXml(self, layer_node, context):
        layerEl = layer_node.toElement()
        self.layer_name = layerEl.attribute("title")
        self.transparency = int(layerEl.attribute("transparency"))
        self.center.setX(float(layerEl.attribute("x")))
        self.center.setY(float(layerEl.attribute("y")))
        self.azimut = float(layerEl.attribute("azimut"))
        self.azimutLeftFL = float(layerEl.attribute("azimutLeftFL"))
        self.azimutRightFL = float(layerEl.attribute("azimutRightFL"))
        self.color = QgsSymbolLayerUtils.decodeColor(layerEl.attribute(
            "color"))
        self.lineWidth = int(layerEl.attribute("lineWidth"))

        self.setCrs(QgsCoordinateReferenceSystem(layerEl.attribute("crs")))
        return True

    def writeXml(self, layer_node, document, context):
        layerEl = layer_node.toElement()
        layerEl.setAttribute("type", "plugin")
        layerEl.setAttribute("name", self.pluginLayerType())
        layerEl.setAttribute("title", self.layer_name)
        layerEl.setAttribute("transparency", self.transparency)
        layerEl.setAttribute("x", self.center.x())
        layerEl.setAttribute("y", self.center.y())
        layerEl.setAttribute("azimut", self.azimut)
        layerEl.setAttribute("azimutLeftFL", self.azimutLeftFL)
        layerEl.setAttribute("azimutRightFL", self.azimutRightFL)
        layerEl.setAttribute("crs", self.crs().authid())
        layerEl.setAttribute("color", QgsSymbolLayerUtils.encodeColor(
            self.color))
        layerEl.setAttribute("lineWidth", self.getLineWidth())
        return True


class Renderer(QgsMapLayerRenderer):
    def __init__(self, layer, rendererContext):
        QgsMapLayerRenderer.__init__(self, layer.id())

        self.layer = layer
        self.rendererContext = rendererContext
        self.geod = Geodesic.WGS84
        self.mDa = QgsDistanceArea()

        self.mDa.setEllipsoid("WGS84")
        self.mDa.setSourceCrs(QgsCoordinateReferenceSystem("EPSG:4326"),
                              QgsProject.instance().transformContext())

    def render(self):
        mapToPixel = self.rendererContext.mapToPixel()
        self.rendererContext.painter().save()
        self.rendererContext.painter().setOpacity((
            100. - self.layer.transparency) / 100.)
        self.rendererContext.painter().setCompositionMode(
            QPainter.CompositionMode_Source)
        self.rendererContext.painter().setPen(
            QPen(self.layer.color, self.layer.lineWidth))

        ct = QgsCoordinateTransform(self.layer.crs(),
                                    QgsCoordinateReferenceSystem("EPSG:4326"),
                                    QgsProject.instance())
        rct = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"),
                                     self.layer.crs(),
                                     QgsProject.instance())

        # draw rings
        wgsCenter = ct.transform(self.layer.center)

        radMeters = 230
        poly = QPolygonF()
        for a in range(361):
            wgsPoint = self.mDa.computeSpheroidProject(
                wgsCenter, radMeters, self.layer.azimutToRadiant(a))
            mapPoint = rct.transform(wgsPoint)
            poly.append(mapToPixel.transform(mapPoint).toQPointF())
        path = QPainterPath()
        path.addPolygon(poly)
        self.rendererContext.painter().drawPath(path)

        # draw axes
        axisRadiusMeters = 1 * QgsUnitTypes.fromUnitToUnitFactor(
            QgsUnitTypes.DistanceNauticalMiles, QgsUnitTypes.DistanceMeters)
        bearing = self.layer.getAzimut(True)
        for counter in range(2):
            wgsPoint = self.mDa.computeSpheroidProject(wgsCenter,
                                                       axisRadiusMeters,
                                                       bearing)
            line = self.geod.InverseLine(wgsCenter.y(), wgsCenter.x(),
                                         wgsPoint.y(), wgsPoint.x())
            dist = line.s13
            sdist = 500
            nSegments = max(1, int(math.ceil(dist / sdist)))
            poly = QPolygonF()
            for iseg in range(nSegments + 1):
                coords = line.Position(iseg * sdist)
                mapPoint = rct.transform(
                    QgsPointXY(coords["lon2"], coords["lat2"]))
                poly.append(mapToPixel.transform(mapPoint).toQPointF())
            line.Position(dist)
            mapPoint = rct.transform(QgsPointXY(
                coords["lon2"], coords["lat2"]))
            poly.append(mapToPixel.transform(mapPoint).toQPointF())
            path = QPainterPath()
            path.addPolygon(poly)
            self.rendererContext.painter().drawPath(path)
            bearing = self.layer.getAzimut(True) + self.layer.azimutToRadiant(
                180)

        # draw flight lines
        self.rendererContext.painter().setPen(QPen(
            self.layer.color, self.layer.lineWidth, Qt.DashLine))
        lineRadiusMeters = 1.5 * QgsUnitTypes.fromUnitToUnitFactor(
            QgsUnitTypes.DistanceNauticalMiles, QgsUnitTypes.DistanceMeters)
        for bearing in [self.layer.getAzimutLeftFL(True),
                        self.layer.getAzimutRightFL(True)]:
            wgsPoint = self.mDa.computeSpheroidProject(
                wgsCenter, lineRadiusMeters, self.layer.getAzimut(
                    True) + bearing)
            line = self.geod.InverseLine(wgsCenter.y(), wgsCenter.x(),
                                         wgsPoint.y(), wgsPoint.x())
            dist = line.s13
            sdist = 50
            nSegments = max(1, int(math.ceil(dist / sdist)))
            poly = QPolygonF()
            for iseg in range(nSegments + 1):
                if iseg in range(2):
                    continue
                coords = line.Position(iseg * sdist)
                mapPoint = rct.transform(
                    QgsPointXY(coords["lon2"], coords["lat2"]))
                poly.append(mapToPixel.transform(mapPoint).toQPointF())
            line.Position(dist)
            mapPoint = rct.transform(
                QgsPointXY(coords["lon2"], coords["lat2"]))
            poly.append(mapToPixel.transform(mapPoint).toQPointF())
            path = QPainterPath()
            path.addPolygon(poly)
            self.rendererContext.painter().drawPath(path)

        self.rendererContext.painter().restore()
        return True


class OverlayPC7LayerType(QgsPluginLayerType):
    def __init__(self):
        QgsPluginLayerType.__init__(self, OverlayPC7Layer.pluginLayerType())

    def createLayer(self):
        return OverlayPC7Layer("OverlayPC7")

    def hasLayerProperties(self):
        return 0
