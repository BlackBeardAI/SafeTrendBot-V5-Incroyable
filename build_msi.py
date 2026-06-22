#!/usr/bin/env python3
"""
SafeTrendBot V5 — Build MSI Installer
======================================
Crée un installateur Windows .msi avec WiX Toolset.

Prérequis (sur Windows):
  1. Python 3.11+ avec pip
  2. WiX Toolset 3.14: https://wixtoolset.org/releases/
     (ajouter candle.exe et light.exe au PATH)
  3. pip install pyinstaller

Usage:
  python build_msi.py              # build complet: exe + msi
  python build_msi.py --exe-only   # seulement le .exe
  python build_msi.py --msi-only   # seulement le .msi (exe déjà buildé)

Le .msi final sera dans: dist/SafeTrendBot-Setup-5.4.0.msi
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

VERSION = "5.4.0"
APP_NAME = "SafeTrendBot"
PUBLISHER = "BlackBeardAI"
ROOT = Path(__file__).parent
TRADING_BOT_DIR = ROOT / "trading_bot"
BUILD_DIR = ROOT / "build_msi"
DIST_DIR = ROOT / "dist"
EXE_NAME = "SafeTrendBot.exe"

# Dossiers WiX
WIX_OBJ_DIR = BUILD_DIR / "wix_obj"


# ═══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 1: Build .exe avec PyInstaller
# ═══════════════════════════════════════════════════════════════════════════════

def build_exe():
    """Build le .exe avec PyInstaller."""
    print("\n" + "=" * 60)
    print("  ÉTAPE 1/3 — Build .exe avec PyInstaller")
    print("=" * 60)

    BUILD_DIR.mkdir(exist_ok=True)

    spec_content = generate_pyinstaller_spec()
    spec_path = BUILD_DIR / "SafeTrendBot.spec"
    spec_path.write_text(spec_content, encoding="utf-8")
    print(f"  [OK] Spec écrit: {spec_path}")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(spec_path),
        "--noconfirm",
        "--clean",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR / "pyinstaller_work"),
    ]

    print(f"  Commande: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(TRADING_BOT_DIR))

    if result.returncode != 0:
        print("[ERREUR] Build PyInstaller échoué")
        return False

    exe_path = DIST_DIR / APP_NAME / EXE_NAME
    if not exe_path.exists():
        print(f"[ERREUR] .exe non trouvé: {exe_path}")
        return False

    print(f"\n  [OK] .exe créé: {exe_path}")
    print(f"       Taille: {exe_path.stat().st_size / 1024 / 1024:.1f} MB")
    return True


def generate_pyinstaller_spec() -> str:
    """Génère le fichier .spec pour PyInstaller."""
    return f'''# -*- mode: python ; coding: utf-8 -*-
# Auto-généré par build_msi.py

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # Inclure les ressources non-Python
        ('app/ui/*.qss', 'app/ui'),
        ('app/ui/assets/*', 'app/ui/assets'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6._QOpenGLWidgets',
        'app.core.trading_engine',
        'app.core.trading_engine_v3',
        'app.core.trading_engine_v4',
        'app.core.config_manager',
        'app.core.strategies',
        'app.brokers.mt5_adapter',
        'app.ui.main_window',
        'app.ui.views.dashboard_view',
        'app.ui.views.positions_view',
        'app.ui.views.backtest_view',
        'app.ui.views.settings_view',
        'app.ui.views.broker_view',
        'app.ui.views.analytics_view',
        'app.ui.views.logs_view',
        'app.ui.views.paper_trading_view',
        'app.ui.views.calendar_view',
        'app.ui.views.news_view',
        'app.ui.views.telegram_view',
        'app.ui.views.market_hours_view',
        'app.ui.views.profiles_view',
        'app.ui.views.trend_analysis_view',
        'app.ui.views.tools_view',
        'app.ui.views.watchlist_view',
        'app.ui.views.recommendations_view',
        'app.ui.views.strategy_params_view',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        # Exclure les modules de protection neutralisés
        'app.core.license_manager_v2',
        'app.core.license_stub',
        'app.core.auto_updater',
        'app.core.broadcast_client',
        'app.core.watermark',
        'app.core.pin_lock',
        'pyarmor',
        'cython',
        'flask',
        'flask_cors',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SafeTrendBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='app/ui/assets/icon.ico' if Path('app/ui/assets/icon.ico').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SafeTrendBot',
)
'''


# ═══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 2: Générer le fichier WiX (.wxs)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_wxs_file() -> Path:
    """Génère le fichier WiX source (.wxs) pour l'installateur MSI."""
    wxs_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="*"
           Name="SafeTrendBot V5"
           Language="1036"
           Version="{VERSION}"
           Manufacturer="{PUBLISHER}"
           UpgradeCode="a3f7b2c1-5d8e-4f6a-9b3c-7e2d1f5a8b6e">

    <Package Id="*"
             Description="Installateur SafeTrendBot V5 — Trading Bot"
             Manufacturer="{PUBLISHER}"
             InstallScope="perMachine"
             InstallerVersion="500"
             Compressed="yes"
             Languages="1036" />

    <MajorUpgrade DowngradeErrorMessage="Une version plus récente est déjà installée." />
    <Media Id="1" Cabinet="SafeTrendBot.cab" EmbedCab="yes" />

    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="ProgramFiles64Folder">
        <Directory Id="INSTALLDIR" Name="SafeTrendBot">
          <Directory Id="AppDir" Name="app">
            <Directory Id="CoreDir" Name="core" />
            <Directory Id="BrokersDir" Name="brokers" />
            <Directory Id="UiDir" Name="ui">
              <Directory Id="ViewsDir" Name="views" />
              <Directory Id="AssetsDir" Name="assets" />
            </Directory>
          </Directory>
          <Directory Id="BotDir" Name="bot" />
          <Directory Id="BacktestDir" Name="backtest" />
        </Directory>
      </Directory>

      <!-- Menu Démarrer -->
      <Directory Id="ProgramMenuFolder">
        <Directory Id="StartMenuDir" Name="SafeTrendBot" />
      </Directory>

      <!-- Bureau -->
      <Directory Id="DesktopFolder" Name="Desktop" />
    </Directory>

    <!-- Composants principaux -->
    <DirectoryRef Id="INSTALLDIR">
      <Component Id="MainExe" Guid="b1c2d3e4-5f6a-7b8c-9d0e-1f2a3b4c5d6e">
        <File Id="SafeTrendBotExe" Source="$(var.SRC)\\SafeTrendBot.exe" KeyPath="yes">
          <Shortcut Id="StartMenuShortcut"
                    Directory="StartMenuDir"
                    Name="SafeTrendBot V5"
                    WorkingDirectory="INSTALLDIR"
                    Icon="AppIcon"
                    IconIndex="0"
                    Advertise="yes" />
          <Shortcut Id="DesktopShortcut"
                    Directory="DesktopFolder"
                    Name="SafeTrendBot V5"
                    WorkingDirectory="INSTALLDIR"
                    Icon="AppIcon"
                    IconIndex="0"
                    Advertise="yes" />
        </File>

        <ProgId Id="SafeTrendBot.config" Description="Configuration SafeTrendBot">
          <Extension Id="stb" ContentType="application/json">
            <Verb Id="open" Command="Ouvrir avec SafeTrendBot" Argument="--config &quot;%1&quot;" />
          </Extension>
        </ProgId>
      </Component>
    </DirectoryRef>

    <!-- Feature principale -->
    <Feature Id="Complete"
             Title="SafeTrendBot V5 — Installation complète"
             Description="Bot de trading automatisé avec interface graphique"
             Level="1"
             ConfigurableDirectory="INSTALLDIR">
      <ComponentRef Id="MainExe" />
      <ComponentGroupRef Id="AppFiles" />
    </Feature>

    <!-- Icône -->
    <Icon Id="AppIcon" SourceFile="$(var.SRC)\\SafeTrendBot.exe" />

    <!-- UI: installation simplifiée -->
    <UI>
      <UIRef Id="WixUI_InstallDir" />
      <Property Id="WIXUI_INSTALLDIR" Value="INSTALLDIR" />
      <Property Id="WIXUI_EXITDIALOGOPTIONALTEXT"
                Value="SafeTrendBot V5 installé avec succès! Cliquez sur Finish pour terminer." />
      <Property Id="WIXUI_EXITDIALOGOPTIONALCHECKBOXTEXT"
                Value="Lancer SafeTrendBot maintenant" />
      <Property Id="WIXUI_EXITDIALOGOPTIONALCHECKBOX" Value="1" />

      <Publish Dialog="ExitDialog"
               Control="Finish"
               Event="EndDialog"
               Value="Return"
               Order="999">1</Publish>
    </UI>

    <!-- Propriétés -->
    <Property Id="ARPHELPLINK" Value="https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable" />
    <Property Id="ARPURLINFOABOUT" Value="https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable" />

    <!-- Actions custom: lancer après install -->
    <CustomAction Id="LaunchApp"
                  FileKey="SafeTrendBotExe"
                  ExeCommand=""
                  Return="asyncNoWait" />

    <InstallExecuteSequence>
      <Custom Action="LaunchApp"
              After="InstallFinalize">
        (NOT Installed) AND (WIXUI_EXITDIALOGOPTIONALCHECKBOX = "1")
      </Custom>
    </InstallExecuteSequence>

    <WixVariable Id="WixUIBannerBmp" Value="$(var.BANNER)" />
    <WixVariable Id="WixUIDialogBmp" Value="$(var.DIALOG)" />
  </Product>
</Wix>
'''
    WIX_OBJ_DIR.mkdir(parents=True, exist_ok=True)
    wxs_path = WIX_OBJ_DIR / "SafeTrendBot.wxs"
    wxs_path.write_text(wxs_content, encoding="utf-8")
    print(f"  [OK] Fichier WiX écrit: {wxs_path}")
    return wxs_path


def generate_harvest_script() -> Path:
    """Génère un script qui 'harvest' les fichiers du dossier _internal."""
    script = f'''<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Fragment>
    <ComponentGroup Id="AppFiles">
      <!-- Ce fragment est généré par heat.exe -->
      <!-- Voir build_msi.py — étape harvest -->
    </ComponentGroup>
  </Fragment>
</Wix>
'''
    path = WIX_OBJ_DIR / "HarvestedFiles.wxs"
    path.write_text(script, encoding="utf-8")
    return path


# ═══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 3: Compiler le MSI
# ═══════════════════════════════════════════════════════════════════════════════

def find_wix():
    """Trouve candle.exe et light.exe (WiX Toolset)."""
    paths = os.environ.get("PATH", "").split(os.pathsep)
    wix_dirs = [
        Path(os.environ.get("WIX", "")),
        Path("C:/Program Files (x86)/WiX Toolset 3.14"),
        Path("C:/Program Files (x86)/WiX Toolset 3.11"),
        Path("C:/Program Files/WiX Toolset 3.14"),
    ]

    for d in wix_dirs:
        bin_dir = d / "bin"
        if (bin_dir / "candle.exe").exists():
            return bin_dir

    # Chercher dans PATH
    for p in paths:
        if (Path(p) / "candle.exe").exists():
            return Path(p)

    return None


def harvest_files(exe_dir: Path) -> Path:
    """Utilise heat.exe pour collecter tous les fichiers du dossier exe."""
    wix_bin = find_wix()
    if not wix_bin:
        print("[ERREUR] WiX Toolset non trouvé")
        print("   Installez WiX 3.14: https://wixtoolset.org/releases/")
        return None

    heat = wix_bin / "heat.exe"
    output = WIX_OBJ_DIR / "HarvestedFiles.wxs"

    # Harvest tout le dossier _internal
    internal_dir = exe_dir / "_internal"
    if not internal_dir.exists():
        # PyInstaller --onedir met les deps dans _internal (v6+)
        internal_dir = exe_dir

    cmd = [
        str(heat),
        "dir", str(internal_dir),
        "-cg", "AppFiles",
        "-dr", "INSTALLDIR",
        "-var", "var.SRC",
        "-out", str(output),
        "-gg",          # générer des GUIDs
        "-sfrag",       # pas de fragments séparés
        "-srd",         # pas de répertoires vides
        "-ke",          # garder les extensions
    ]

    print(f"  Harvest: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("[ERREUR] heat.exe a échoué")
        return None

    print(f"  [OK] Fichiers harvestés: {output}")
    return output


def compile_msi():
    """Compile le .msi avec candle.exe + light.exe."""
    print("\n" + "=" * 60)
    print("  ÉTAPE 3/3 — Compilation MSI")
    print("=" * 60)

    wix_bin = find_wix()
    if not wix_bin:
        print("\n[ERREUR] WiX Toolset non trouvé!")
        print("   Installez WiX Toolset 3.14:")
        print("   https://wixtoolset.org/releases/")
        print("   Et ajoutez le dossier bin au PATH")
        return False

    exe_dir = DIST_DIR / APP_NAME
    if not exe_dir.exists():
        print(f"[ERREUR] Dossier exe non trouvé: {exe_dir}")
        print("   Lancez d'abord: python build_msi.py --exe-only")
        return False

    # 1. Harvest les fichiers
    harvested = harvest_files(exe_dir)
    if not harvested:
        return False

    # 2. Générer le .wxs principal
    wxs = generate_wxs_file()

    # 3. Préparer les variables WiX
    src_var = str(exe_dir).replace("\\", "\\\\")
    banner = str(WIX_OBJ_DIR / "banner.bmp")
    dialog = str(WIX_OBJ_DIR / "dialog.bmp")

    # Créer des images placeholder si elles n'existent pas
    create_placeholder_images()

    # 4. candle.exe — compiler .wxs → .wixobj
    candle = wix_bin / "candle.exe"
    wixobj = WIX_OBJ_DIR / "SafeTrendBot.wixobj"
    harvested_obj = WIX_OBJ_DIR / "HarvestedFiles.wixobj"

    cmd_candle = [
        str(candle),
        str(wxs),
        str(harvested),
        "-o", str(WIX_OBJ_DIR) + "\\",
        "-dSRC=" + src_var,
        "-dBANNER=" + banner,
        "-dDIALOG=" + dialog,
        "-ext", "WixUIExtension",
        "-ext", "WixUtilExtension",
    ]

    print(f"\n  Candle: {' '.join(cmd_candle)}")
    result = subprocess.run(cmd_candle)
    if result.returncode != 0:
        print("[ERREUR] candle.exe a échoué")
        return False

    # 5. light.exe — lier .wixobj → .msi
    light = wix_bin / "light.exe"
    msi_output = DIST_DIR / f"SafeTrendBot-Setup-{VERSION}.msi"

    cmd_light = [
        str(light),
        str(wixobj),
        str(harvested_obj),
        "-o", str(msi_output),
        "-ext", "WixUIExtension",
        "-ext", "WixUtilExtension",
        "-cultures:fr-fr",
        "-b", str(WIX_OBJ_DIR),
    ]

    print(f"\n  Light: {' '.join(cmd_light)}")
    result = subprocess.run(cmd_light)
    if result.returncode != 0:
        print("[ERREUR] light.exe a échoué")
        return False

    if msi_output.exists():
        print(f"\n{'=' * 60}")
        print(f"  [OK] MSI créé: {msi_output}")
        print(f"       Taille: {msi_output.stat().st_size / 1024 / 1024:.1f} MB")
        print(f"{'=' * 60}")
        return True
    return False


def create_placeholder_images():
    """Crée des images placeholder pour WiX si elles n'existent pas."""
    # Banner: 493x63
    banner = WIX_OBJ_DIR / "banner.bmp"
    dialog = WIX_OBJ_DIR / "dialog.bmp"

    if not banner.exists() or not dialog.exists():
        print("  [INFO] Création des images placeholder pour WiX")
        try:
            from PIL import Image, ImageDraw
            for path, size, bg in [
                (banner, (493, 63), (26, 31, 46)),
                (dialog, (493, 312), (26, 31, 46)),
            ]:
                img = Image.new("RGB", size, bg)
                draw = ImageDraw.Draw(img)
                draw.text((size[0]//2 - 80, size[1]//2 - 10),
                          "SafeTrendBot V5", fill=(0, 217, 255))
                img.save(path)
            print(f"  [OK] Images créées: {banner}, {dialog}")
        except ImportError:
            print("  [WARN] PIL non installé — pas d'images custom pour WiX")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Build MSI installer pour SafeTrendBot")
    parser.add_argument("--exe-only", action="store_true",
                        help="Seulement build le .exe")
    parser.add_argument("--msi-only", action="store_true",
                        help="Seulement compiler le .msi (exe déjà buildé)")
    args = parser.parse_args()

    print(f"\n{'=' * 60}")
    print(f"  SafeTrendBot V{VERSION} — Build MSI Installer")
    print(f"{'=' * 60}")

    success = True

    if not args.msi_only:
        success = build_exe()
        if not success or args.exe_only:
            return 0 if success else 1

    if not args.exe_only:
        success = compile_msi()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())