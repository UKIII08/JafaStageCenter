#include "Parameters.h"

using namespace juce;

namespace
{
    StringArray gIDs;

    struct Collector
    {
        AudioProcessorValueTreeState::ParameterLayout layout;

        void add (std::unique_ptr<RangedAudioParameter> p)
        {
            gIDs.addIfNotAlreadyThere (p->getParameterID());
            layout.add (std::move (p));
        }
    };

    ParameterID pv (const char* id) { return { id, 1 }; }

    NormalisableRange<float> range (float lo, float hi, float skewCentre)
    {
        NormalisableRange<float> r (lo, hi);
        r.setSkewForCentre (skewCentre);
        return r;
    }

    String pct (float v, int)      { return String (roundToInt (v * 100.0f)) + " %"; }
    String dB  (float v, int)      { return String (v, 1) + " dB"; }
    String ms  (float v, int)      { return v >= 1000.0f ? String (v / 1000.0f, 2) + " s"
                                                         : String (roundToInt (v)) + " ms"; }
    String cents (float v, int)    { return String (v, 1) + " ct"; }
    String hz  (float v, int)      { return v >= 1000.0f ? String (v / 1000.0f, 2) + " kHz"
                                                         : String (roundToInt (v)) + " Hz"; }
    String sec (float v, int)      { return String (v, 2) + " s"; }
    String mult (float v, int)     { return String (v, 2) + " x"; }
}

AudioProcessorValueTreeState::ParameterLayout createParameterLayout()
{
    gIDs.clear();
    Collector c;

    auto f = [] (const char* id, const char* name, NormalisableRange<float> r, float def,
                 std::function<String (float, int)> fmt)
    {
        return std::make_unique<AudioParameterFloat> (pv (id), name, r, def,
                                                      AudioParameterFloatAttributes().withStringFromValueFunction (std::move (fmt)));
    };

    // ---- Piano engine ------------------------------------------------------
    c.add (std::make_unique<AudioParameterChoice> (pv (pid::model), "Model",
              StringArray { "Concert Grand", "Warm Upright", "Felt Piano", "Stage Bright" }, 0));

    c.add (f (pid::brightness,   "Brightness",  range (-1.0f, 1.0f, 0.0f),   0.0f,  [] (float v, int) { return String (v, 2); }));
    c.add (f (pid::hardness,     "Hammer",      range (0.0f, 1.0f, 0.5f),    0.5f,  pct));
    c.add (f (pid::decayTime,    "Decay",       range (0.4f, 2.0f, 1.0f),    1.0f,  mult));
    c.add (f (pid::detune,       "Unison",      range (0.0f, 20.0f, 6.0f),   5.0f,  cents));
    c.add (f (pid::stretch,      "Stretch",     range (0.0f, 2.0f, 1.0f),    1.0f,  mult));
    c.add (f (pid::sympathetic,  "Resonance",   range (0.0f, 1.0f, 0.5f),    0.35f, pct));
    c.add (f (pid::mechNoise,    "Mechanics",   range (0.0f, 1.0f, 0.5f),    0.30f, pct));
    c.add (f (pid::velCurve,     "Vel Curve",   range (0.0f, 1.0f, 0.5f),    0.5f,  pct));
    c.add (f (pid::dynamicRange, "Dynamics",    range (6.0f, 42.0f, 24.0f),  26.0f, dB));
    c.add (f (pid::pianoWidth,   "Spread",      range (0.0f, 1.0f, 0.5f),    0.45f, pct));
    c.add (f (pid::pianoLevel,   "Piano",       range (-24.0f, 6.0f, -6.0f), 0.0f,  dB));

    // ---- Pad layer ---------------------------------------------------------
    c.add (f (pid::padLevel,     "Pad",         range (-60.0f, 0.0f, -24.0f), -60.0f, dB));
    c.add (f (pid::padTone,      "Pad Tone",    range (200.0f, 8000.0f, 1400.0f), 1600.0f, hz));
    c.add (f (pid::padAttack,    "Pad Attack",  range (5.0f, 4000.0f, 500.0f), 700.0f, ms));
    c.add (f (pid::padRelease,   "Pad Release", range (50.0f, 8000.0f, 1500.0f), 2200.0f, ms));
    c.add (f (pid::padDetune,    "Pad Detune",  range (0.0f, 30.0f, 10.0f),  12.0f, cents));

    // ---- Tone & drive ------------------------------------------------------
    c.add (f (pid::eqLow,        "Low",         range (-12.0f, 12.0f, 0.0f), 0.0f, dB));
    c.add (f (pid::eqMid,        "Mid",         range (-12.0f, 12.0f, 0.0f), 0.0f, dB));
    c.add (f (pid::eqHigh,       "High",        range (-12.0f, 12.0f, 0.0f), 0.0f, dB));
    c.add (f (pid::eqAir,        "Air",         range (0.0f, 12.0f, 4.0f),   2.0f, dB));
    c.add (f (pid::compAmount,   "Compress",    range (0.0f, 1.0f, 0.5f),    0.35f, pct));
    c.add (f (pid::compMix,      "Comp Mix",    range (0.0f, 1.0f, 0.5f),    1.0f, pct));
    c.add (f (pid::drive,        "Drive",       range (0.0f, 1.0f, 0.4f),    0.18f, pct));
    c.add (f (pid::driveTone,    "Drive Tone",  range (0.0f, 1.0f, 0.5f),    0.5f, pct));

    // ---- Movement ----------------------------------------------------------
    c.add (f (pid::chorusAmount, "Chorus",      range (0.0f, 1.0f, 0.4f),    0.15f, pct));
    c.add (f (pid::chorusRate,   "Chorus Rate", range (0.05f, 4.0f, 0.7f),   0.35f, [] (float v, int) { return String (v, 2) + " Hz"; }));

    // ---- Delay -------------------------------------------------------------
    c.add (f (pid::delayMix,     "Delay",       range (0.0f, 1.0f, 0.35f),   0.0f, pct));
    c.add (std::make_unique<AudioParameterBool> (pv (pid::delaySync), "Delay Sync", true));
    c.add (std::make_unique<AudioParameterChoice> (pv (pid::delayDiv), "Delay Div",
              StringArray { "1/4", "1/4T", "1/8.", "1/8", "1/8T", "1/16.", "1/16" }, 2));
    c.add (f (pid::delayMs,      "Delay Time",  range (20.0f, 2000.0f, 400.0f), 420.0f, ms));
    c.add (f (pid::delayFeedback,"Feedback",    range (0.0f, 0.95f, 0.45f),  0.38f, pct));
    c.add (f (pid::delayTone,    "Delay Tone",  range (0.0f, 1.0f, 0.5f),    0.45f, pct));
    c.add (f (pid::delayPingPong,"Ping Pong",   range (0.0f, 1.0f, 0.5f),    0.7f, pct));

    // ---- Reverb ------------------------------------------------------------
    c.add (f (pid::reverbMix,    "Reverb",      range (0.0f, 1.0f, 0.35f),   0.28f, pct));
    c.add (f (pid::reverbSize,   "Size",        range (0.0f, 1.0f, 0.5f),    0.6f, pct));
    c.add (f (pid::reverbDecay,  "Decay Time",  range (0.4f, 15.0f, 3.5f),   3.2f, sec));
    c.add (f (pid::reverbTone,   "Rev Tone",    range (0.0f, 1.0f, 0.5f),    0.5f, pct));
    c.add (f (pid::reverbPredelay,"Predelay",   range (0.0f, 200.0f, 40.0f), 20.0f, ms));
    c.add (f (pid::shimmer,      "Shimmer",     range (0.0f, 1.0f, 0.4f),    0.0f, pct));

    // ---- Output ------------------------------------------------------------
    c.add (f (pid::width,        "Width",       range (0.0f, 2.0f, 1.0f),    1.0f, pct));
    c.add (f (pid::outputGain,   "Output",      range (-24.0f, 12.0f, 0.0f), 0.0f, dB));

    return std::move (c.layout);
}

const StringArray& allParameterIDs()
{
    return gIDs;
}
