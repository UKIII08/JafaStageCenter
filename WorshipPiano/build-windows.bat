@echo off
setlocal
cd /d "%~dp0"

echo.
echo  ==========================================================
echo    Jafa Worship Piano  -  budowanie i instalacja (Windows)
echo  ==========================================================
echo.

REM Wtyczka jest katalogiem, a nie plikiem, wiec kopiujemy przez robocopy.
set "PLUGIN_DIR=build\JafaWorshipPiano_artefacts\Release\VST3\Jafa Worship Piano.vst3"
set "SYSTEM_DIR=%CommonProgramFiles%\VST3"
set "USER_DIR=%LOCALAPPDATA%\Programs\Common\VST3"

REM ===========================================================================
REM  1. CMake
REM ===========================================================================
set "CMAKE="
where cmake >nul 2>&1
if not errorlevel 1 set "CMAKE=cmake"
if defined CMAKE goto :haveCMake

REM Visual Studio dowozi wlasnego CMake - szukamy go w typowych miejscach.
for /d %%V in ("%ProgramFiles%\Microsoft Visual Studio\2022\*")      do call :tryVsCMake "%%V"
for /d %%V in ("%ProgramFiles(x86)%\Microsoft Visual Studio\2022\*")  do call :tryVsCMake "%%V"
for /d %%V in ("%ProgramFiles(x86)%\Microsoft Visual Studio\2019\*")  do call :tryVsCMake "%%V"

if defined CMAKE goto :haveCMake

echo  [BLAD] Nie znaleziono CMake.
echo.
echo  Zainstaluj Visual Studio 2022 Community i przy instalacji zaznacz
echo  skladnik "Desktop development with C++" (Tworzenie aplikacji klasycznych
echo  w C++). CMake jest w nim zawarty - nie trzeba go instalowac osobno.
echo.
echo    https://visualstudio.microsoft.com/downloads/
echo.
pause
exit /b 1

:tryVsCMake
if defined CMAKE goto :eof
set "CANDIDATE=%~1\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
if exist "%CANDIDATE%" set "CMAKE=%CANDIDATE%"
goto :eof

:haveCMake
echo  CMake: %CMAKE%
echo.

REM ===========================================================================
REM  2. Konfiguracja. Pierwszy przebieg pobiera JUCE.
REM ===========================================================================
echo  [1/3] Konfiguracja...
echo        (przy pierwszym uruchomieniu pobierany jest JUCE - to potrwa)
echo.

"%CMAKE%" -B build -G "Visual Studio 17 2022" -A x64
if not errorlevel 1 goto :configured

echo.
echo  Generator "Visual Studio 17 2022" nie zadzialal, probuje domyslnego...
echo.
REM Kasujemy tylko cache, nie caly folder build - w build\_deps siedzi pobrany
REM JUCE i szkoda go sciagac drugi raz.
del /q build\CMakeCache.txt >nul 2>&1
rmdir /s /q build\CMakeFiles >nul 2>&1
"%CMAKE%" -B build -DCMAKE_BUILD_TYPE=Release
if not errorlevel 1 goto :configured

echo.
echo  [BLAD] Konfiguracja nie powiodla sie.
echo.
echo  Najczestsze przyczyny:
echo    - brak polaczenia z internetem (przy pierwszym razie pobierany jest JUCE)
echo    - brak skladnika "Desktop development with C++" w Visual Studio
echo.
pause
exit /b 1

:configured
echo.
echo  [2/3] Kompilacja...
echo.
"%CMAKE%" --build build --config Release --parallel
if errorlevel 1 goto :buildFailed

if not exist "%PLUGIN_DIR%" goto :missingPlugin

REM ===========================================================================
REM  3. Instalacja
REM ===========================================================================
echo.
echo  [3/3] Instalacja...
echo.

REM Zaladowana wtyczka jest zablokowana przez host - kopiowanie sie nie uda.
tasklist /fi "imagename eq reaper.exe" 2>nul | find /i "reaper.exe" >nul
if not errorlevel 1 echo  UWAGA: Reaper jest uruchomiony. Jesli kopiowanie sie nie uda, zamknij go i uruchom skrypt ponownie.

set "TARGET="
robocopy "%PLUGIN_DIR%" "%SYSTEM_DIR%\Jafa Worship Piano.vst3" /E /NJH /NJS /NDL /NFL /R:1 /W:1 >nul 2>&1
if errorlevel 8 goto :tryUserDir
set "TARGET=%SYSTEM_DIR%"
goto :installed

:tryUserDir
echo  Brak uprawnien do "%SYSTEM_DIR%" - instaluje w folderze uzytkownika.
if not exist "%USER_DIR%" mkdir "%USER_DIR%" >nul 2>&1
robocopy "%PLUGIN_DIR%" "%USER_DIR%\Jafa Worship Piano.vst3" /E /NJH /NJS /NDL /NFL /R:1 /W:1 >nul 2>&1
if errorlevel 8 goto :copyFailed
set "TARGET=%USER_DIR%"
set "NEEDS_PATH=1"

:installed
echo.
echo  ==========================================================
echo    Gotowe.
echo.
echo    Zainstalowano w:
echo      %TARGET%
echo.
echo    W Reaperze:
if defined NEEDS_PATH echo      0. Options - Preferences - Plug-ins - VST - Edit path list
if defined NEEDS_PATH echo         i dodaj sciezke powyzej
echo      1. Options - Preferences - Plug-ins - VST - Re-scan
echo      2. Na sciezce MIDI: FX - zakladka Instruments -
echo         "VSTi: Jafa Worship Piano (Jafa Stage)"
echo.
echo    Zacznij od presetu "Soaking Grand".
echo  ==========================================================
echo.
pause
exit /b 0

:buildFailed
echo.
echo  [BLAD] Kompilacja nie powiodla sie. Przewin wyzej - pierwszy blad
echo         w logu mowi wiecej niz ostatni.
echo.
pause
exit /b 1

:missingPlugin
echo.
echo  [BLAD] Kompilacja przeszla, ale nie znaleziono wtyczki w:
echo         %CD%\%PLUGIN_DIR%
echo.
pause
exit /b 1

:copyFailed
echo.
echo  [BLAD] Nie udalo sie skopiowac wtyczki.
echo         Jesli Reaper jest uruchomiony - zamknij go i sprobuj ponownie.
echo.
echo         Mozesz tez skopiowac recznie ten folder:
echo           %CD%\%PLUGIN_DIR%
echo         do:
echo           %SYSTEM_DIR%
echo.
pause
exit /b 1
