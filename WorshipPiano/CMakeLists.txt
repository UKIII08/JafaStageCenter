cmake_minimum_required(VERSION 3.22)

project(JafaWorshipPiano VERSION 1.0.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_OSX_DEPLOYMENT_TARGET "10.13" CACHE STRING "Minimum macOS version")
set(CMAKE_OSX_ARCHITECTURES "x86_64;arm64" CACHE STRING "macOS architectures")

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

# ---------------------------------------------------------------------------
# JUCE
#
# Set JUCE_SOURCE_DIR to a local checkout to skip the download, e.g.
#   cmake -B build -DJUCE_SOURCE_DIR=/path/to/JUCE
# ---------------------------------------------------------------------------
set(JUCE_SOURCE_DIR "" CACHE PATH "Path to a local JUCE checkout (optional)")

if(JUCE_SOURCE_DIR AND EXISTS "${JUCE_SOURCE_DIR}/CMakeLists.txt")
    message(STATUS "Using local JUCE from ${JUCE_SOURCE_DIR}")
    add_subdirectory("${JUCE_SOURCE_DIR}" "${CMAKE_BINARY_DIR}/JUCE" EXCLUDE_FROM_ALL)
else()
    include(FetchContent)
    FetchContent_Declare(
        JUCE
        GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
        GIT_TAG        8.0.15
        GIT_SHALLOW    TRUE
    )
    FetchContent_MakeAvailable(JUCE)
endif()

juce_add_plugin(JafaWorshipPiano
    COMPANY_NAME                "Jafa Stage"
    BUNDLE_ID                   "com.jafastage.worshippiano"
    PLUGIN_MANUFACTURER_CODE    Jafa
    PLUGIN_CODE                 Jwp1
    FORMATS                     VST3 Standalone
    PRODUCT_NAME                "Jafa Worship Piano"
    IS_SYNTH                    TRUE
    NEEDS_MIDI_INPUT            TRUE
    NEEDS_MIDI_OUTPUT           FALSE
    IS_MIDI_EFFECT              FALSE
    EDITOR_WANTS_KEYBOARD_FOCUS FALSE
    COPY_PLUGIN_AFTER_BUILD     FALSE
    VST3_CATEGORIES             Instrument Synth Piano
)

target_sources(JafaWorshipPiano PRIVATE
    Source/PluginProcessor.cpp
    Source/PluginEditor.cpp
    Source/Parameters.cpp
    Source/Presets.cpp
    Source/dsp/PianoEngine.cpp
    Source/dsp/PadLayer.cpp
    Source/dsp/EffectChain.cpp
    Source/dsp/Ambience.cpp
    Source/gui/WorshipLookAndFeel.cpp
    Source/gui/PresetBar.cpp
)

target_compile_definitions(JafaWorshipPiano PUBLIC
    JUCE_WEB_BROWSER=0
    JUCE_USE_CURL=0
    JUCE_VST3_CAN_REPLACE_VST2=0
    JUCE_DISPLAY_SPLASH_SCREEN=0
    JUCE_STRICT_REFCOUNTEDPOINTER=1
)

target_include_directories(JafaWorshipPiano PRIVATE Source)

target_link_libraries(JafaWorshipPiano PRIVATE
    juce::juce_audio_utils
    juce::juce_dsp
PUBLIC
    juce::juce_recommended_config_flags
    juce::juce_recommended_lto_flags
    juce::juce_recommended_warning_flags
)

# ---------------------------------------------------------------------------
# Offline render harness - renders every factory preset to a WAV and checks the
# DSP for NaNs, runaway feedback and silence. Not part of the plugin build.
# ---------------------------------------------------------------------------
option(WORSHIPPIANO_BUILD_TOOLS "Build the offline render harness" OFF)

if(WORSHIPPIANO_BUILD_TOOLS)
    juce_add_console_app(WorshipPianoRender PRODUCT_NAME "WorshipPianoRender")

    target_sources(WorshipPianoRender PRIVATE
        tools/OfflineRender.cpp
        Source/PluginProcessor.cpp
        Source/PluginEditor.cpp
        Source/Parameters.cpp
        Source/Presets.cpp
        Source/dsp/PianoEngine.cpp
        Source/dsp/PadLayer.cpp
        Source/dsp/EffectChain.cpp
    Source/dsp/Ambience.cpp
        Source/gui/WorshipLookAndFeel.cpp
        Source/gui/PresetBar.cpp
    )

    target_compile_definitions(WorshipPianoRender PRIVATE
        JUCE_WEB_BROWSER=0
        JUCE_USE_CURL=0
        JUCE_STANDALONE_APPLICATION=1
        JucePlugin_Name="Jafa Worship Piano"
    )

    target_include_directories(WorshipPianoRender PRIVATE Source)

    target_link_libraries(WorshipPianoRender PRIVATE
        juce::juce_audio_utils
        juce::juce_dsp
    PUBLIC
        juce::juce_recommended_config_flags
        juce::juce_recommended_warning_flags
    )
endif()
