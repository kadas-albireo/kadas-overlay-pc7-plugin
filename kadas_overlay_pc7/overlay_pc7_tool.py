import os

from PyQt4 import uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *

from overlay_pc7_layer import OverlayPC7Layer

OverlayPC7WidgetBase = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'overlay_pc7_dialog_base.ui'))[0]


class OverlayPC7Tool(QgsMapTool):

    def __init__(self, iface):
        QgsMapTool.__init__(self, iface.mapCanvas())

        self.iface = iface
        self.picking = False
        self.layerTreeView = iface.layerTreeView()
        self.widget = OverlayPC7Widget(self.iface)
        self.widget.setVisible(False)
        self.mapLayerRegistry = QgsMapLayerRegistry.instance()

        self.widget.requestPickCenter.connect(self.setPicking)
        self.widget.close.connect(self.close)

        self.actionEditLayer = QAction(self.tr("Edit"), self)
        self.actionEditLayer.setIcon(QIcon(
            ":/images/themes/default/mIconEditable.png"))
        self.actionEditLayer.triggered.connect(self.editCurrentLayer)
        self.layerTreeView.menuProvider().addLegendLayerAction(
            self.actionEditLayer, "", "edit_overlaypc7_layer",
            QgsMapLayer.PluginLayer, False)

        QgsMapLayerRegistry.instance().layerWasAdded.connect(
            self.addLayerTreeMenuAction)
        QgsMapLayerRegistry.instance().layerWillBeRemoved.connect(
            self.removeLayerTreeMenuAction)

    def activate(self):
        if isinstance(self.iface.mapCanvas().currentLayer(), OverlayPC7Layer):
            self.widget.setLayer(self.iface.mapCanvas().currentLayer())
        else:
            found = False
            for layer in self.mapLayerRegistry.mapLayers().values():
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
            self.layerTreeView.menuProvider().addLegendLayerActionForLayer(
                "edit_overlaypc7_layer", mapLayer)

    def removeLayerTreeMenuAction(self, mapLayerId):
        mapLayer = self.mapLayerRegistry.mapLayer(mapLayerId)
        if isinstance(mapLayer, OverlayPC7Layer):
            self.layerTreeView.menuProvider().removeLegendLayerActionsForLayer(
                mapLayer)

    def editCurrentLayer(self):
        if isinstance(self.iface.mapCanvas().currentLayer(), OverlayPC7Layer):
            self.iface.mapCanvas().setMapTool(self)

    def tr(self, message):
        return QCoreApplication.translate('OverlayPC7', message)


class OverlayPC7Widget(QgsBottomBar, OverlayPC7WidgetBase):

    requestPickCenter = pyqtSignal()
    close = pyqtSignal()

    def __init__(self, iface):
        QgsBottomBar.__init__(self, iface.mapCanvas())

        self.iface = iface
        self.layerTreeView = iface.layerTreeView()
        self.currentLayer = None
        self.mapLayerRegistry = QgsMapLayerRegistry.instance()

        self.setLayout(QHBoxLayout())
        self.layout().setSpacing(10)

        base = QWidget()
        self.setupUi(base)
        self.layout().addWidget(base)

        closeButton = QPushButton()
        closeButton.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        closeButton.setIcon(QIcon(":/images/themes/default/mIconClose.png"))
        closeButton.setToolTip(self.tr("Close"))
        closeButton.clicked.connect(self.close)
        self.layout().addWidget(closeButton)
        self.layout().setAlignment(closeButton, Qt.AlignTop)

        self.toolButtonAddLayer.clicked.connect(self.createLayer)
        self.inputCenter.coordinateChanged.connect(self.updateLayer)
        self.toolButtonPickCenter.clicked.connect(self.requestPickCenter)
        self.spinBoxAzimut.valueChanged.connect(self.updateLayer)
        self.spinBoxAzimutFL.valueChanged.connect(self.updateLayer)
        self.spinBoxLineWidth.valueChanged.connect(self.updateLineWidth)
        self.toolButtonColor.colorChanged.connect(self.updateColor)

        QgsMapLayerRegistry.instance().layersAdded.connect(
            self.repopulateLayers)
        QgsMapLayerRegistry.instance().layersRemoved.connect(
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
                22.5, 45)
            self.mapLayerRegistry.addMapLayer(overlayPC7Layer)
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
        self.spinBoxAzimutFL.blockSignals(True)
        self.spinBoxAzimutFL.setValue(self.currentLayer.getAzimutFL())
        self.spinBoxAzimutFL.blockSignals(False)
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
        azimut_fl = self.spinBoxAzimutFL.value()
        self.currentLayer.setup(center, crs, azimut, azimut_fl)
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
        for layer in self.mapLayerRegistry.mapLayers().values():
            if isinstance(layer, OverlayPC7Layer):
                layer.layerNameChanged.connect(self.repopulateLayers)
                self.comboBoxLayer.addItem(layer.name(), layer.id())
                if self.iface.mapCanvas().currentLayer() == layer:
                    current = idx
                idx += 1
        self.comboBoxLayer.setCurrentIndex(-1)
        self.comboBoxLayer.blockSignals(False)
        self.comboBoxLayer.setCurrentIndex(current)
        self.widgetLayerSetup.setEnabled(self.comboBoxLayer.count() > 0)

    def currentLayerChanged(self, cur):
        layer = self.mapLayerRegistry.mapLayer(
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