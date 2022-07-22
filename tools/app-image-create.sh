#!/usr/bin/env bash
set -e
cd `dirname $0`

if [ ! -f linuxdeploy-plugin-conda.sh ]; then
    wget -nc "https://raw.githubusercontent.com/TheAssassin/linuxdeploy-plugin-conda/master/linuxdeploy-plugin-conda.sh"
    chmod +x linuxdeploy-plugin-conda.sh
fi

if [ ! -f linuxdeploy-x86_64.AppImage ]; then
    wget -nc "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage"
    chmod +x linuxdeploy-x86_64.AppImage
fi

if [ ! -f appimagetool-x86_64.AppImage ]; then
    wget -nc "https://github.com/AppImage/AppImageKit/releases/download/13/appimagetool-x86_64.AppImage"
    chmod +x appimagetool-x86_64.AppImage
fi

rm -rf AppDir

APP_RUN='#! /bin/bash

APPDIR=`dirname $0`

# Else, resources from the AppImage mount to $PATH, and use sandboxed
# Python3 from AppImage
export PATH="$PATH":"${APPDIR}"/usr/bin
${APPDIR}/usr/bin/python3 ${APPDIR}/opt/database-dossier/database-dossier.py $@0'

# Set Environment
export CONDA_CHANNELS='conda-forge'
export CONDA_PACKAGES='PyQtWebKit'
export PIP_REQUIREMENTS='appdirs mysql_connector_python Pygments'
#export PIP_REQUIREMENTS='pywebview appdirs mysql_connector_repackaged Pygments'

mkdir -p ./AppDir/opt/database-dossier/artwork
cp ../artwork/*.png ./AppDir/opt/database-dossier/artwork/
cp ../database-dossier.py ./AppDir/opt/database-dossier
cp -R ../database_dossier ./AppDir/opt/database-dossier
cp -R ../doc ./AppDir/opt/database-dossier

echo "$APP_RUN" > ./AppDir/AppRun.sh

./linuxdeploy-x86_64.AppImage \
    --appdir AppDir \
    -i ../artwork/database-dossier.png \
    -d ../artwork/database-dossier.desktop \
    --plugin conda \
    --custom-apprun ./AppDir/AppRun.sh \
    --output appimage

sed -i 's/QtCore.QMetaObject.connectSlotsByName(self.toplevelWidget)/#QtCore.QMetaObject.connectSlotsByName(self.toplevelWidget)/g' AppDir/usr/conda/lib/python3.9/site-packages/PyQt5/uic/uiparser.py

rm Database_Dossier*.AppImage

./appimagetool-x86_64.AppImage AppDir

mkdir -p ../release
mv Database_Dossier*.AppImage ../release
ls -l ../release