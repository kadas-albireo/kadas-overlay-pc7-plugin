import os

from qgis.PyQt import uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.core import *
from qgis.gui import *
from kadas.kadasgui import *

from .overlay_pc7_layer import OverlayPC7Layer

OverlayPC7WidgetBase = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'overlay_pc7_dialog_base.ui'))[0]


class OverlayPC7Tool(QgsMapTool):

    def __init__(self, iface):
        QgsMapTool.__init__(self, iface.mapCanvas())

        self.iface = iface
        self.picking = False
        self.widget = OverlayPC7Widget(self.iface)
        self.widget.setVisible(False)
        self.qgsProject = QgsProject.instance()

        self.widget.requestPickCenter.connect(self.setPicking)
        self.widget.close.connect(self.close)

        self.actionEditLayer = QAction(self.tr("Edit"), self)
        self.actionEditLayer.setIcon(QIcon(
            ":/images/themes/default/mIconEditable.png"))
        self.actionEditLayer.triggered.connect(self.editCurrentLayer)
        self.iface.addCustomActionForLayerType(
            self.actionEditLayer, "edit_overlaypc7_layer",
            QgsMapLayer.PluginLayer, False)

        QgsProject.instance().layerWasAdded.connect(
            self.addLayerTreeMenuAction)
        QgsProject.instance().layerWillBeRemoved.connect(
            self.removeLayerTreeMenuAction)

    def activate(self):
        if isinstance(self.iface.mapCanvas().currentLayer(), OverlayPC7Layer):
            self.widget.setLayer(self.iface.mapCanvas().currentLayer())
        else:
            found = False
            for layer in self.qgsProject.mapLayers().values():
                if isinstance(layer, OverlayPC7Layer):
                    self.widget.setLayer(layer)
                    found = True
                    break
            if not found:
                self.widget.createLayer(self.tr("OverlayPC7"))
        self.widget.setVisible(True)

    def deactivate(self):
        self.widget.setVisible(False)
        self.picking = False
        self.setCursor(Qt.ArrowCursor)

    def canvasReleaseEvent(self, event):
        if self.picking:
            self.widget.centerPicked(self.toMapCoordinates(event.pos()))
            self.setPicking(False)
        elif event.button() == Qt.RightButton:
            self.iface.mapCanvas().unsetMapTool(self)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.picking:
                self.setPicking(False)
            else:
                self.iface.mapCanvas().unsetMapTool(self)

    def setPicking(self, picking=True):
        self.picking = picking
        self.setCursor(Qt.CrossCursor if picking else Qt.ArrowCursor)

    def close(self):
        self.iface.mapCanvas().unsetMapTool(self)

    def addLayerTreeMenuAction(self, mapLayer):
        if isinstance(mapLayer, OverlayPC7Layer):
            self.iface.addCustomActionForLayer(
                self.actionEditLayer, mapLayer)

    def removeLayerTreeMenuAction(self, mapLayerId):
        mapLayer = self.qgsProject.mapLayer(mapLayerId)
        if isinstance(mapLayer, OverlayPC7Layer):
            self.iface.removeCustomActionForLayerType(
                self.actionEditLayer)

    def editCurrentLayer(self):
        if isinstance(self.iface.mapCanvas().currentLayer(), OverlayPC7Layer):
            self.iface.mapCanvas().setMapTool(self)

    def tr(self, message):
        return QCoreApplication.translate('OverlayPC7', message)


class OverlayPC7Widget(KadasBottomBar, OverlayPC7WidgetBase):

    requestPickCenter = pyqtSignal()
    close = pyqtSignal()

    def __init__(self, iface):
        KadasBottomBar.__init__(self, iface.mapCanvas())

        self.iface = iface
        self.layerTreeView = iface.layerTreeView()
        self.currentLayer = None
        self.qgsProject = QgsProject.instance()

        self.setLayout(QHBoxLayout())
        self.layout().setSpacing(10)

        base = QWidget()
        self.setupUi(base)
        self.layout().addWidget(base)

        closeButton = QPushButton()
        closeButton.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        closeButton.setIcon(QIcon(":/kadas/icons/close"))
        closeButton.setToolTip(self.tr("Close"))
        closeButton.clicked.connect(self.close)
        self.layout().addWidget(closeButton)
        self.layout().setAlignment(closeButton, Qt.AlignTop)

        self.toolButtonAddLayer.clicked.connect(self.createLayer)
        self.inputCenter.coordinateChanged.connect(self.updateLayer)
        self.toolButtonPickCenter.clicked.connect(self.requestPickCenter)
        self.spinBoxAzimut.valueChanged.connect(self.updateLayer)
        self.spinBoxLeftFL.valueChanged.connect(self.updateLayer)
        self.spinBoxRightFL.valueChanged.connect(self.updateLayer)
        self.spinBoxLineWidth.valueChanged.connect(self.updateLineWidth)
        self.toolButtonColor.colorChanged.connect(self.updateColor)

        QgsProject.instance().layersAdded.connect(
            self.repopulateLayers)
        QgsProject.instance().layersRemoved.connect(
            self.repopulateLayers)
        self.iface.mapCanvas().currentLayerChanged.connect(
            self.updateSelectedLayer)

        self.repopulateLayers()
        self.comboBoxLayer.currentIndexChanged.connect(
            self.currentLayerChanged)

    def centerPicked(self, pos):
        self.inputCenter.setCoordinate(
            pos, self.iface.mapCanvas().mapSettings().destinationCrs())

    def createLayer(self, layerName):
        if not layerName:
            layerName = QInputDialog.getText(
                self, self.tr("Layer Name"),
                self.tr("Enter name of new layer:"))[0]
        if layerName:
            overlayPC7Layer = OverlayPC7Layer(layerName)
            overlayPC7Layer.setup(
                self.iface.mapCanvas().extent().center(),
                self.iface.mapCanvas().mapSettings().destinationCrs(),
                22.5, 45, 135)
            self.qgsProject.addMapLayer(overlayPC7Layer)
            self.setLayer(overlayPC7Layer)

    def setLayer(self, layer):
        if layer == self.currentLayer:
            return

        self.currentLayer = layer if isinstance(layer, OverlayPC7Layer) else False

        if not self.currentLayer:
            self.widgetLayerSetup.setEnabled(False)
            return
        self.comboBoxLayer.blockSignals(True)
        self.comboBoxLayer.setCurrentIndex(self.comboBoxLayer.findData(
            self.currentLayer.id()))
        self.comboBoxLayer.blockSignals(False)
        self.layerTreeView.setLayerVisible(self.currentLayer, True)
        self.iface.mapCanvas().setCurrentLayer(self.currentLayer)

        self.inputCenter.blockSignals(True)
        self.inputCenter.setCoordinate(self.currentLayer.getCenter(),
                                       self.currentLayer.crs())
        self.inputCenter.blockSignals(False)
        self.spinBoxAzimut.blockSignals(True)
        self.spinBoxAzimut.setValue(self.currentLayer.getAzimut())
        self.spinBoxAzimut.blockSignals(False)
        self.spinBoxLeftFL.blockSignals(True)
        self.spinBoxLeftFL.setValue(self.currentLayer.getAzimutLeftFL())
        self.spinBoxLeftFL.blockSignals(False)
        self.spinBoxRightFL.blockSignals(True)
        self.spinBoxRightFL.setValue(self.currentLayer.getAzimutRightFL())
        self.spinBoxRightFL.blockSignals(False)
        self.spinBoxLineWidth.blockSignals(True)
        self.spinBoxLineWidth.setValue(self.currentLayer.getLineWidth())
        self.spinBoxLineWidth.blockSignals(False)
        self.toolButtonColor.blockSignals(True)
        self.toolButtonColor.setColor(self.currentLayer.getColor())
        self.toolButtonColor.blockSignals(False)
        self.widgetLayerSetup.setEnabled(True)

    def updateLayer(self):
        if not self.currentLayer or self.inputCenter.isEmpty():
            return
        center = self.inputCenter.getCoordinate()
        crs = self.inputCenter.getCrs()
        azimut = self.spinBoxAzimut.value()
        azimutLeftFL = self.spinBoxLeftFL.value()
        azimutRightFL = self.spinBoxRightFL.value()
        self.currentLayer.setup(center, crs, azimut, azimutLeftFL, azimutRightFL)
        self.currentLayer.triggerRepaint()

    def updateColor(self, color):
        if self.currentLayer:
            self.currentLayer.setColor(color)
            self.currentLayer.triggerRepaint()

    def updateLineWidth(self, width):
        if self.currentLayer:
            self.currentLayer.setLineWidth(width)
            self.currentLayer.triggerRepaint()

    def repopulateLayers(self):
        if self.comboBoxLayer.signalsBlocked():
            return
        self.comboBoxLayer.blockSignals(True)
        self.comboBoxLayer.clear()
        idx = 0
        current = 0
        for layer in self.qgsProject.mapLayers().values():
            if isinstance(layer, OverlayPC7Layer):
                layer.nameChanged.connect(self.repopulateLayers)
                self.comboBoxLayer.addItem(layer.name(), layer.id())
                if self.iface.mapCanvas().currentLayer() == layer:
                    current = idx
                idx += 1
        self.comboBoxLayer.setCurrentIndex(-1)
        self.comboBoxLayer.blockSignals(False)
        self.comboBoxLayer.setCurrentIndex(current)
        self.widgetLayerSetup.setEnabled(self.comboBoxLayer.count() > 0)

    def currentLayerChanged(self, cur):
        layer = self.qgsProject.mapLayer(
            self.comboBoxLayer.itemData(cur))
        if isinstance(layer, OverlayPC7Layer):
            self.setLayer(layer)
        else:
            self.widgetLayerSetup.setEnabled(False)

    def updateSelectedLayer(self, layer):
        if not layer:
            return
        if isinstance(layer, OverlayPC7Layer):
            self.setLayer(layer)

    def tr(self, message):
        return QCoreApplication.translate('OverlayPC7', message)
