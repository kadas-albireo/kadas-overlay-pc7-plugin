# -*- coding: utf-8 -*-
"""
/***************************************************************************
 OverlayPS7
                                 A QGIS plugin
 This plugin paints an overlay
                              -------------------
        begin                : 2018-12-17
        git sha              : $Format:%H$
        copyright            : (C) 2018 by Sourcepole AG
        email                : smani@sourcepole.ch
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon
import resources_rc
from overlay_ps_7_tool import OverlayPS7Tool
from overlay_ps_7_layer import OverlayPS7LayerType
import os.path
from qgis.core import *


class OverlayPS7:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgisInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'overlayps7_{0}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        self.overlay_7_tool = OverlayPS7Tool(self.iface)

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('OverlayPS7', message)

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/OverlayPS7/icon.png'
        icon = QIcon(icon_path)

        self.action = QAction(icon, self.tr(u'Overlay PS 7'),
                              self.iface.mainWindow())
        self.action.triggered.connect(self.activateTool)
        self.action.setEnabled(True)

        self.iface.addAction(self.action, self.iface.PLUGIN_MENU,
                             self.iface.NO_TOOLBAR, self.iface.DRAW_TAB)

        self.pluginLayerType = OverlayPS7LayerType()
        QgsPluginLayerRegistry.instance().addPluginLayerType(self.pluginLayerType)

    def unload(self):
        pass

    def activateTool(self):
        self.iface.mapCanvas().setMapTool(self.overlay_7_tool)
