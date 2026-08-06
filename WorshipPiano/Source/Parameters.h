#pragma once

#include <juce_audio_processors/juce_audio_processors.h>

namespace pid
{
    // --- Piano engine -------------------------------------------------------
    inline constexpr const char* model        = "model";        // Grand / Upright / Felt / Stage
    inline constexpr const char* brightness   = "brightness";   // loop-filter damping
    inline constexpr const char* hardness     = "hardness";     // hammer hardness
    inline constexpr const char* decayTime    = "decay";        // T60 multiplier
    inline constexpr const char* detune       = "detune";       // unison detune (cents)
    inline constexpr const char* stretch      = "stretch";      // inharmonicity / dispersion
    inline constexpr const char* sympathetic  = "sympathetic";  // pedal-down resonance
    inline constexpr const char* mechNoise    = "mechnoise";    // hammer + damper noise
    inline constexpr const char* velCurve     = "velcurve";     // velocity response curve
    inline constexpr const char* dynamicRange = "dynrange";     // vel -> level range (dB)
    inline constexpr const char* pianoWidth   = "pianowidth";   // key-position stereo spread
    inline constexpr const char* pianoLevel   = "pianolevel";

    // --- Pad layer ----------------------------------------------------------
    inline constexpr const char* padLevel     = "padlevel";
    inline constexpr const char* padTone      = "padtone";
    inline constexpr const char* padAttack    = "padattack";
    inline constexpr const char* padRelease   = "padrelease";
    inline constexpr const char* padDetune    = "paddetune";

    // --- Tone & drive -------------------------------------------------------
    inline constexpr const char* eqLow        = "eqlow";
    inline constexpr const char* eqMid        = "eqmid";
    inline constexpr const char* eqHigh       = "eqhigh";
    inline constexpr const char* eqAir        = "eqair";
    inline constexpr const char* compAmount   = "compamount";
    inline constexpr const char* compMix      = "compmix";
    inline constexpr const char* drive        = "drive";
    inline constexpr const char* driveTone    = "drivetone";

    // --- Movement -----------------------------------------------------------
    inline constexpr const char* chorusAmount = "chorusamount";
    inline constexpr const char* chorusRate   = "chorusrate";

    // --- Delay --------------------------------------------------------------
    inline constexpr const char* delayMix     = "delaymix";
    inline constexpr const char* delaySync    = "delaysync";     // bool
    inline constexpr const char* delayDiv     = "delaydiv";      // choice
    inline constexpr const char* delayMs      = "delayms";
    inline constexpr const char* delayFeedback= "delayfb";
    inline constexpr const char* delayTone    = "delaytone";
    inline constexpr const char* delayPingPong= "delayping";

    // --- Reverb -------------------------------------------------------------
    inline constexpr const char* reverbMix    = "reverbmix";
    inline constexpr const char* reverbSize   = "reverbsize";
    inline constexpr const char* reverbDecay  = "reverbdecay";
    inline constexpr const char* reverbTone   = "reverbtone";
    inline constexpr const char* reverbPredelay = "reverbpre";
    inline constexpr const char* shimmer      = "shimmer";

    // --- Output -------------------------------------------------------------
    inline constexpr const char* width        = "width";
    inline constexpr const char* outputGain   = "outgain";
}

juce::AudioProcessorValueTreeState::ParameterLayout createParameterLayout();

/** Every parameter ID, in layout order - used by the preset system. */
const juce::StringArray& allParameterIDs();
