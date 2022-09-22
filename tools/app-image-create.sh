#!/usr/bin/env bash
set -e
cd `dirname $0`
VERSION='1.0.0'

# Will create a https://appimage.org/

# [Get the tools]
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

# ------------------------------------------------------------------------------
# [Prepair the ingredients]
APP_RUN='#! /bin/bash
APPDIR=`dirname $0`
export PATH="$PATH":"${APPDIR}"/usr/bin
${APPDIR}/usr/bin/python3 ${APPDIR}/opt/database-dossier/database-dossier.py $@'

export CONDA_CHANNELS='conda-forge'

# I think PyWebkit looks nicer than the new QtWebEngine
export CONDA_PACKAGES='PyQtWebKit'

# Install PyQt5 at this point - will insrtall the correct version
export PIP_REQUIREMENTS='appdirs mysql_connector_python Pygments pyqt5'

# [Pour everything into a large bowl]
mkdir -p ./AppDir/opt/database-dossier/artwork
cp ../artwork/*.png ./AppDir/opt/database-dossier/artwork/
cp ../database-dossier.py ./AppDir/opt/database-dossier
cp -R ../database_dossier ./AppDir/opt/database-dossier
cp -R ../doc ./AppDir/opt/database-dossier

echo "$APP_RUN" > ./AppDir/AppRun.sh

# ------------------------------------------------------------------------------
# [Stir until well mixed]
./linuxdeploy-x86_64.AppImage \
    --appdir AppDir \
    -i ../artwork/database-dossier.png \
    -d ../artwork/database-dossier.desktop \
    --plugin conda \
    --custom-apprun ./AppDir/AppRun.sh \
    --output appimage

# The version of PyQt that is compatibile with PyQtWebKit has a nasty bug
# this change makes things work
sed -i 's/QtCore.QMetaObject.connectSlotsByName(self.toplevelWidget)/#QtCore.QMetaObject.connectSlotsByName(self.toplevelWidget)/g' AppDir/usr/conda/lib/python3.9/site-packages/PyQt5/uic/uiparser.py

mkdir -p AppDir/usr/share/metainfo/
echo '<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
    <id>com.nshiell.database-dossier</id>
    <metadata_license>CC0-1.0</metadata_license>
    <project_license>GPL-3.0</project_license>
    <name>Database Dossier</name>
    <summary>Query your databases</summary>
    <description>
        <p>Query your databases.</p>
    </description>
    <launchable type="desktop-id">database-dossier.desktop</launchable>
    <url type="homepage">https://nshiell.com/database-dossier</url>
    <screenshots>
        <screenshot type="default">
            <image>https://nshiell.com/database-dossier/screenshot-kde.png.png</image>
        </screenshot>
    </screenshots>
    <provides>
        <id>database-dossier.desktop</id>
    </provides>
</component>' > AppDir/usr/share/metainfo/com.nshiell.database-dossier.xml

rm Database_Dossier*.AppImage

# ------------------------------------------------------------------------------
# [Preheat the oven upto gas mark 6 and wait for it to bake]
./appimagetool-x86_64.AppImage AppDir --sign

# ------------------------------------------------------------------------------
# [serve with garnish]
mkdir -p ../release
mv Database_Dossier*.AppImage "../release/Database-Dossier-$VERSION.AppImage"
ls -l ../release
