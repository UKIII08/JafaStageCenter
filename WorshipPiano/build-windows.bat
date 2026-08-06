@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ===============================================
echo   Jafa Worship Piano - budowanie dla Windows
echo ===============================================
echo.

REM ---------------------------------------------------------------------------
REM CMake: albo w PATH, albo ten dolaczony do Visual Studio
REM ---------------------------------------------------------------------------
set "CMAKE="
where cmake >nul 2>&1 && set "CMAKE=cmake"

if "%CMAKE%"=="" (
    for /d %%V in ("%ProgramFiles%\Microsoft Visual Studio\2022\*") do (
        if exist "%%V\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" (
            set "CMAKE=%%V\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
        )
    )
)

if "%CMAKE%"=="" (
    echo [BLAD] Nie znaleziono CMake.
    echo.
    echo Potrzebujesz Visual Studio 2022 Community z zaznaczonym skladnikiem
    echo "Desktop development with C++" - CMake jest w nim zawarty.
    echo Pobierz: https://visualstudio.microsoft.com/downloads/
    echo.
    pause
    exit /b 1
)

echo CMake: %CMAKE%
echo.

REM ---------------------------------------------------------------------------
REM Konfiguracja i build. Pierwszy przebieg pobiera JUCE - to potrwa.
REM ---------------------------------------------------------------------------
echo [1/3] Konfiguracja (pierwszy raz pobiera JUCE, moze potrwac kilka minut)...
"%CMAKE%" -B build -A x64
if errorlevel 1 (
    echo.
    echo [BLAD] Konfiguracja nie powiodla sie. Sprawdz polaczenie z internetem
    echo        - przy pierwszym uruchomieniu pobierany jest JUCE.
    pause
    exit /b 1
)

echo.
echo [2/3] Kompilacja...
"%CMAKE%" --build build --config Release --parallel
if errorlevel 1 (
    echo.
    echo [BLAD] Kompilacja nie powiodla sie.
    pause
    exit /b 1
)

set "PLUGIN=build\JafaWorshipPiano_artefacts\Release\VST3\Jafa Worship Piano.vst3"

if not exist "%PLUGIN%" (
    echo [BLAD] Nie znaleziono zbudowanej wtyczki w %PLUGIN%
    pause
    exit /b 1
)

REM ---------------------------------------------------------------------------
REM Instalacja: najpierw systemowy folder VST3, a jesli brak uprawnien -
REM ten uzytkownika. Wtyczka VST3 na Windows to katalog, nie pojedynczy plik.
REM ---------------------------------------------------------------------------
echo.
echo [3/3] Instalacja...

set "SYSTEM_DIR=%CommonProgramFiles%\VST3"
set "USER_DIR=%LOCALAPPDATA%\Programs\Common\VST3"
set "TARGET="

robocopy "%PLUGIN%" "%SYSTEM_DIR%\Jafa Worship Piano.vst3" /E /NJH /NJS /NDL /NFL >nul 2>&1
if not errorlevel 8 set "TARGET=%SYSTEM_DIR%"

if "%TARGET%"=="" (
    echo Brak uprawnien do "%SYSTEM_DIR%", instaluje w folderze uzytkownika.
    if not exist "%USER_DIR%" mkdir "%USER_DIR%" >nul 2>&1
    robocopy "%PLUGIN%" "%USER_DIR%\Jafa Worship Piano.vst3" /E /NJH /NJS /NDL /NFL >nul 2>&1
    if not errorlevel 8 set "TARGET=%USER_DIR%"
)

if "%TARGET%"=="" (
    echo.
    echo [BLAD] Nie udalo sie skopiowac wtyczki.
    echo        Skopiuj recznie folder:
    echo          %CD%\%PLUGIN%
    echo        do: %SYSTEM_DIR%
    pause
    exit /b 1
)

echo.
echo ===============================================
echo   Gotowe.
echo.
echo   Zainstalowano w:
echo   !TARGET!
echo.
echo   W Reaperze:
echo     1. Options - Preferences - Plug-ins - VST
if /i not "!TARGET!"=="%SYSTEM_DIR%" (
    echo        Dodaj sciezke: !TARGET!
)
echo     2. Kliknij "Re-scan"
echo     3. Na scieszce MIDI: FX - Instruments -
echo        "VSTi: Jafa Worship Piano (Jafa Stage)"
echo ===============================================
echo.
pause
