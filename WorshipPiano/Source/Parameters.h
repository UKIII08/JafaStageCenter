#pragma once

#include <juce_audio_processors/juce_audio_processors.h>

/*
    Deliberately small control set. Everything that only ever had one sensible
    value is fixed in the code instead of being exposed as a knob - the presets
    are meant to be played, not dialled in.
*/
namespace pid
{
    // --- Piano --------------------------------------------------------------
    inline constexpr const char* model        = "model";     // voicing
    inline constexpr const char* tone         = "tone";      // dark .. bright
    inline constexpr const char* attack       = "attack";    // hammer noise / thump
    inline constexpr const char* decayTime    = "decay";     // sustain length
    inline constexpr const char* dynamicRange = "dynrange";  // velocity range
    inline constexpr const char* pianoLevel   = "pianolevel";

    // --- Pad layer ----------------------------------------------------------
    inline constexpr const char* padLevel     = "padlevel";
    inline constexpr const char* padTone      = "padtone";
    inline constexpr const char* padAttack    = "padattack";
    inline constexpr const char* padRelease   = "padrelease";

    // --- Tone & drive -------------------------------------------------------
    inline constexpr const char* eqLow        = "eqlow";
    inline constexpr const char* eqHigh       = "eqhigh";
    inline constexpr const char* eqAir        = "eqair";
    inline constexpr const char* compAmount   = "compamount";
    inline constexpr const char* drive        = "drive";

    // --- Movement & delay ---------------------------------------------------
    inline constexpr const char* chorusAmount = "chorusamount";
    inline constexpr const char* delayMix     = "delaymix";
    inline constexpr const char* delayFeedback= "delayfb";
    inline constexpr const char* delaySync    = "delaysync";
    inline constexpr const char* delayDiv     = "delaydiv";

    // --- Ambience -----------------------------------------------------------
    inline constexpr const char* reverbMachine= "revmachine";
    inline constexpr const char* reverbMix    = "reverbmix";
    inline constexpr const char* reverbSize   = "reverbsize";
    inline constexpr const char* reverbDecay  = "reverbdecay";
    inline constexpr const char* shimmer      = "shimmer";
    inline constexpr const char* shimmerMode  = "shimmermode";
    inline constexpr const char* reverbDuck   = "reverbduck";
    inline constexpr const char* reverbFreeze = "reverbfreeze";

    // --- Soak macro ---------------------------------------------------------
    inline constexpr const char* soak         = "soak";

    // --- Output -------------------------------------------------------------
    inline constexpr const char* width        = "width";
    inline constexpr const char* outputGain   = "outgain";
}

juce::AudioProcessorValueTreeState::ParameterLayout createParameterLayout();

/** Every parameter ID, in layout order - used by the preset system. */
const juce::StringArray& allParameterIDs();
