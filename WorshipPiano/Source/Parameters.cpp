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

    String pct (float v, int)  { return String (roundToInt (v * 100.0f)) + " %"; }
    String dB  (float v, int)  { return String (v, 1) + " dB"; }
    String ms  (float v, int)  { return v >= 1000.0f ? String (v / 1000.0f, 2) + " s"
                                                     : String (roundToInt (v)) + " ms"; }
    String hz  (float v, int)  { return v >= 1000.0f ? String (v / 1000.0f, 2) + " kHz"
                                                     : String (roundToInt (v)) + " Hz"; }
    String sec (float v, int)  { return String (v, 2) + " s"; }
    String mult (float v, int) { return String (v, 2) + " x"; }
    String bipolar (float v, int)
    {
        if (std::abs (v) < 0.005f) return "0";
        return (v > 0.0f ? String ("+") : String()) + String (v, 2);
    }
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

    // ---- Piano -------------------------------------------------------------
    c.add (std::make_unique<AudioParameterChoice> (pv (pid::model), "Model",
              StringArray { "Smooth Grand", "Bright Grand", "Warm Upright", "Felt Piano" }, 0));

    c.add (f (pid::tone,         "Tone",     range (-1.0f, 1.0f, 0.0f),   0.0f,  bipolar));
    c.add (f (pid::attack,       "Attack",   range (0.0f, 1.0f, 0.5f),    0.35f, pct));
    c.add (f (pid::decayTime,    "Sustain",  range (0.5f, 2.0f, 1.0f),    1.0f,  mult));
    c.add (f (pid::dynamicRange, "Dynamics", range (6.0f, 40.0f, 24.0f),  26.0f, dB));
    c.add (f (pid::pianoLevel,   "Piano",    range (-24.0f, 6.0f, -6.0f), 0.0f,  dB));

    // ---- Pad layer ---------------------------------------------------------
    c.add (f (pid::padLevel,   "Pad",     range (-60.0f, 0.0f, -24.0f), -60.0f, dB));
    c.add (f (pid::padTone,    "Pad Tone",range (200.0f, 8000.0f, 1400.0f), 1600.0f, hz));
    c.add (f (pid::padAttack,  "Swell",   range (5.0f, 4000.0f, 500.0f), 700.0f, ms));
    c.add (f (pid::padRelease, "Release", range (50.0f, 8000.0f, 1500.0f), 2200.0f, ms));

    // ---- Tone & drive ------------------------------------------------------
    c.add (f (pid::eqLow,      "Warmth",   range (-12.0f, 12.0f, 0.0f), 0.0f, dB));
    c.add (f (pid::eqHigh,     "Presence", range (-12.0f, 12.0f, 0.0f), 0.0f, dB));
    c.add (f (pid::eqAir,      "Air",      range (0.0f, 12.0f, 4.0f),   2.0f, dB));
    c.add (f (pid::compAmount, "Compress", range (0.0f, 1.0f, 0.5f),    0.30f, pct));
    c.add (f (pid::drive,      "Drive",    range (0.0f, 1.0f, 0.4f),    0.12f, pct));

    // ---- Movement & delay --------------------------------------------------
    c.add (f (pid::chorusAmount, "Chorus",  range (0.0f, 1.0f, 0.4f),   0.10f, pct));
    c.add (f (pid::delayMix,     "Delay",   range (0.0f, 1.0f, 0.35f),  0.0f,  pct));
    c.add (f (pid::delayFeedback,"Feedback",range (0.0f, 0.90f, 0.42f), 0.38f, pct));

    c.add (std::make_unique<AudioParameterBool> (pv (pid::delaySync), "Delay Sync", true));
    c.add (std::make_unique<AudioParameterChoice> (pv (pid::delayDiv), "Delay Div",
              StringArray { "1/4", "1/4T", "1/8.", "1/8", "1/8T", "1/16.", "1/16" }, 2));

    // ---- Space -------------------------------------------------------------
    c.add (f (pid::reverbMix,   "Reverb",  range (0.0f, 1.0f, 0.35f), 0.26f, pct));
    c.add (f (pid::reverbSize,  "Size",    range (0.0f, 1.0f, 0.5f),  0.55f, pct));
    c.add (f (pid::reverbDecay, "Decay",   range (0.4f, 15.0f, 3.5f), 3.0f,  sec));
    c.add (f (pid::shimmer,     "Shimmer", range (0.0f, 1.0f, 0.4f),  0.0f,  pct));

    // ---- Output ------------------------------------------------------------
    c.add (f (pid::width,      "Width",  range (0.0f, 2.0f, 1.0f),    1.0f, pct));
    c.add (f (pid::outputGain, "Output", range (-24.0f, 12.0f, 0.0f), 0.0f, dB));

    return std::move (c.layout);
}

const StringArray& allParameterIDs()
{
    return gIDs;
}
