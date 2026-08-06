#include "Presets.h"
#include "Parameters.h"

using namespace juce;

namespace presets
{

/*
    Fifteen starting points covering the sounds people actually reach for on a
    Sunday: a clean grand for hymns, the bright compressed stage piano with a
    dotted eighth delay that modern worship records live on, and the felt and
    shimmer territory used for ambient moments and pads under a talk.
*/
const std::vector<Preset>& factory()
{
    static const std::vector<Preset> list =
    {
        { "Sunday Morning", "Classic",
          "Clean concert grand with a warm room. The safe default.",
          { { pid::model, 0 }, { pid::brightness, 0.05f }, { pid::hardness, 0.45f },
            { pid::decayTime, 1.0f }, { pid::detune, 5.0f }, { pid::sympathetic, 0.40f },
            { pid::mechNoise, 0.30f }, { pid::dynamicRange, 26.0f },
            { pid::eqLow, 1.0f }, { pid::eqMid, -0.5f }, { pid::eqHigh, 1.0f }, { pid::eqAir, 2.5f },
            { pid::compAmount, 0.30f }, { pid::drive, 0.12f }, { pid::chorusAmount, 0.08f },
            { pid::delayMix, 0.0f },
            { pid::reverbMix, 0.30f }, { pid::reverbSize, 0.60f }, { pid::reverbDecay, 2.8f },
            { pid::reverbTone, 0.50f }, { pid::reverbPredelay, 20.0f }, { pid::shimmer, 0.0f },
            { pid::padLevel, -60.0f } } },

        { "Arena Anthem", "Modern",
          "Bright, compressed and huge - the big chorus sound.",
          { { pid::model, 3 }, { pid::brightness, 0.35f }, { pid::hardness, 0.70f },
            { pid::decayTime, 1.1f }, { pid::detune, 6.0f }, { pid::sympathetic, 0.45f },
            { pid::dynamicRange, 20.0f },
            { pid::eqLow, 2.0f }, { pid::eqMid, -2.0f }, { pid::eqHigh, 3.0f }, { pid::eqAir, 5.0f },
            { pid::compAmount, 0.55f }, { pid::drive, 0.25f }, { pid::chorusAmount, 0.18f },
            { pid::delayMix, 0.32f }, { pid::delaySync, 1 }, { pid::delayDiv, 2 },
            { pid::delayFeedback, 0.42f }, { pid::delayTone, 0.50f }, { pid::delayPingPong, 0.80f },
            { pid::reverbMix, 0.42f }, { pid::reverbSize, 0.75f }, { pid::reverbDecay, 4.5f },
            { pid::reverbTone, 0.60f }, { pid::reverbPredelay, 30.0f }, { pid::shimmer, 0.08f },
            { pid::padLevel, -60.0f }, { pid::outputGain, -1.0f } } },

        { "Upper Room", "Ambient",
          "Felt hammers, long shimmer and a pad underneath. For the quiet moment.",
          { { pid::model, 2 }, { pid::brightness, -0.15f }, { pid::hardness, 0.25f },
            { pid::decayTime, 1.2f }, { pid::detune, 8.0f }, { pid::sympathetic, 0.60f },
            { pid::mechNoise, 0.45f }, { pid::dynamicRange, 30.0f },
            { pid::eqMid, -1.5f }, { pid::eqHigh, 1.0f }, { pid::eqAir, 3.0f },
            { pid::compAmount, 0.40f }, { pid::drive, 0.20f }, { pid::chorusAmount, 0.30f },
            { pid::delayMix, 0.28f }, { pid::delayDiv, 3 }, { pid::delayFeedback, 0.50f },
            { pid::delayTone, 0.35f }, { pid::delayPingPong, 0.85f },
            { pid::reverbMix, 0.55f }, { pid::reverbSize, 0.90f }, { pid::reverbDecay, 8.0f },
            { pid::reverbTone, 0.45f }, { pid::reverbPredelay, 45.0f }, { pid::shimmer, 0.45f },
            { pid::padLevel, -20.0f }, { pid::padTone, 1200.0f }, { pid::padAttack, 1200.0f },
            { pid::padRelease, 3500.0f }, { pid::padDetune, 15.0f } } },

        { "Intimate Prayer", "Classic",
          "Soft, close and dry. Sits right under a spoken voice.",
          { { pid::model, 0 }, { pid::brightness, -0.20f }, { pid::hardness, 0.30f },
            { pid::decayTime, 1.0f }, { pid::detune, 4.0f }, { pid::sympathetic, 0.35f },
            { pid::mechNoise, 0.40f }, { pid::dynamicRange, 32.0f },
            { pid::eqLow, 0.5f }, { pid::eqHigh, -1.0f }, { pid::eqAir, 1.5f },
            { pid::compAmount, 0.25f }, { pid::drive, 0.08f }, { pid::chorusAmount, 0.05f },
            { pid::delayMix, 0.0f },
            { pid::reverbMix, 0.22f }, { pid::reverbSize, 0.35f }, { pid::reverbDecay, 1.6f },
            { pid::reverbTone, 0.40f }, { pid::reverbPredelay, 8.0f }, { pid::shimmer, 0.0f },
            { pid::padLevel, -60.0f } } },

        { "Felt & Tape", "Ambient",
          "Cloth over the hammers, tape saturation and a slow wobble.",
          { { pid::model, 2 }, { pid::brightness, -0.35f }, { pid::hardness, 0.15f },
            { pid::decayTime, 0.9f }, { pid::detune, 9.0f }, { pid::stretch, 1.2f },
            { pid::sympathetic, 0.50f }, { pid::mechNoise, 0.60f }, { pid::dynamicRange, 28.0f },
            { pid::eqLow, 1.5f }, { pid::eqMid, -1.0f }, { pid::eqHigh, -2.5f }, { pid::eqAir, 0.0f },
            { pid::compAmount, 0.45f }, { pid::compMix, 0.80f },
            { pid::drive, 0.45f }, { pid::driveTone, 0.30f },
            { pid::chorusAmount, 0.35f }, { pid::chorusRate, 0.22f },
            { pid::delayMix, 0.12f }, { pid::delayDiv, 3 }, { pid::delayFeedback, 0.30f },
            { pid::delayTone, 0.25f },
            { pid::reverbMix, 0.35f }, { pid::reverbSize, 0.50f }, { pid::reverbDecay, 2.6f },
            { pid::reverbTone, 0.32f }, { pid::reverbPredelay, 12.0f }, { pid::shimmer, 0.05f },
            { pid::padLevel, -60.0f } } },

        { "Stage Clean", "Live",
          "Dry and forward for playing live through a PA. Add the house reverb yourself.",
          { { pid::model, 3 }, { pid::brightness, 0.20f }, { pid::hardness, 0.60f },
            { pid::decayTime, 1.0f }, { pid::detune, 4.0f }, { pid::sympathetic, 0.30f },
            { pid::dynamicRange, 24.0f },
            { pid::eqLow, 0.5f }, { pid::eqHigh, 1.5f }, { pid::eqAir, 3.0f },
            { pid::compAmount, 0.35f }, { pid::drive, 0.06f }, { pid::chorusAmount, 0.0f },
            { pid::delayMix, 0.0f },
            { pid::reverbMix, 0.10f }, { pid::reverbSize, 0.40f }, { pid::reverbDecay, 1.2f },
            { pid::reverbPredelay, 5.0f }, { pid::shimmer, 0.0f },
            { pid::padLevel, -60.0f } } },

        { "Pad Underneath", "Modern",
          "Piano with a swelling synth bed locked to the same notes.",
          { { pid::model, 0 }, { pid::brightness, 0.0f }, { pid::hardness, 0.45f },
            { pid::sympathetic, 0.45f }, { pid::eqAir, 3.0f },
            { pid::compAmount, 0.35f }, { pid::drive, 0.15f }, { pid::chorusAmount, 0.12f },
            { pid::delayMix, 0.18f }, { pid::delayDiv, 2 }, { pid::delayFeedback, 0.35f },
            { pid::reverbMix, 0.35f }, { pid::reverbSize, 0.65f }, { pid::reverbDecay, 3.6f },
            { pid::reverbPredelay, 25.0f }, { pid::shimmer, 0.12f },
            { pid::padLevel, -14.0f }, { pid::padTone, 1800.0f }, { pid::padAttack, 900.0f },
            { pid::padRelease, 2600.0f }, { pid::padDetune, 12.0f } } },

        { "Shimmer Cloud", "Ambient",
          "Octave-up wash that keeps blooming long after you let go.",
          { { pid::model, 2 }, { pid::brightness, -0.10f }, { pid::hardness, 0.20f },
            { pid::decayTime, 1.4f }, { pid::detune, 10.0f }, { pid::sympathetic, 0.70f },
            { pid::mechNoise, 0.35f }, { pid::dynamicRange, 34.0f }, { pid::pianoLevel, -3.0f },
            { pid::eqLow, -1.0f }, { pid::eqMid, -2.0f }, { pid::eqHigh, 2.0f }, { pid::eqAir, 6.0f },
            { pid::compAmount, 0.50f }, { pid::drive, 0.20f },
            { pid::chorusAmount, 0.45f }, { pid::chorusRate, 0.18f },
            { pid::delayMix, 0.35f }, { pid::delayDiv, 3 }, { pid::delayFeedback, 0.55f },
            { pid::delayTone, 0.40f }, { pid::delayPingPong, 0.90f },
            { pid::reverbMix, 0.60f }, { pid::reverbSize, 1.0f }, { pid::reverbDecay, 12.0f },
            { pid::reverbTone, 0.55f }, { pid::reverbPredelay, 60.0f }, { pid::shimmer, 0.75f },
            { pid::padLevel, -18.0f }, { pid::padTone, 1000.0f }, { pid::padAttack, 1800.0f },
            { pid::padRelease, 5000.0f }, { pid::padDetune, 18.0f },
            { pid::width, 1.25f } } },

        { "Gospel Bright", "Live",
          "Hard hammers and heavy glue compression. Cuts through a full band.",
          { { pid::model, 3 }, { pid::brightness, 0.45f }, { pid::hardness, 0.80f },
            { pid::decayTime, 0.95f }, { pid::detune, 5.0f }, { pid::sympathetic, 0.30f },
            { pid::dynamicRange, 18.0f },
            { pid::eqLow, 2.5f }, { pid::eqMid, 1.0f }, { pid::eqHigh, 2.5f }, { pid::eqAir, 3.5f },
            { pid::compAmount, 0.65f }, { pid::compMix, 0.90f },
            { pid::drive, 0.30f }, { pid::driveTone, 0.60f }, { pid::chorusAmount, 0.05f },
            { pid::delayMix, 0.0f },
            { pid::reverbMix, 0.20f }, { pid::reverbSize, 0.45f }, { pid::reverbDecay, 1.8f },
            { pid::reverbTone, 0.60f }, { pid::reverbPredelay, 12.0f },
            { pid::padLevel, -60.0f }, { pid::outputGain, -1.5f } } },

        { "Cinematic Swell", "Ambient",
          "Dark, slow and enormous. Underscore for a moment of prayer.",
          { { pid::model, 2 }, { pid::brightness, -0.25f }, { pid::hardness, 0.20f },
            { pid::decayTime, 1.5f }, { pid::detune, 7.0f }, { pid::sympathetic, 0.65f },
            { pid::dynamicRange, 30.0f },
            { pid::eqLow, 2.0f }, { pid::eqMid, -2.5f }, { pid::eqAir, 2.0f },
            { pid::compAmount, 0.40f }, { pid::drive, 0.22f }, { pid::chorusAmount, 0.25f },
            { pid::delayMix, 0.22f }, { pid::delayDiv, 0 }, { pid::delayFeedback, 0.45f },
            { pid::delayTone, 0.30f }, { pid::delayPingPong, 0.70f },
            { pid::reverbMix, 0.55f }, { pid::reverbSize, 0.95f }, { pid::reverbDecay, 9.0f },
            { pid::reverbTone, 0.35f }, { pid::reverbPredelay, 70.0f }, { pid::shimmer, 0.30f },
            { pid::padLevel, -12.0f }, { pid::padTone, 900.0f }, { pid::padAttack, 2500.0f },
            { pid::padRelease, 6000.0f }, { pid::padDetune, 16.0f },
            { pid::width, 1.30f } } },

        { "Upright Chapel", "Classic",
          "Small warm upright with plenty of mechanical character.",
          { { pid::model, 1 }, { pid::brightness, -0.05f }, { pid::hardness, 0.45f },
            { pid::decayTime, 0.95f }, { pid::detune, 7.0f }, { pid::stretch, 1.3f },
            { pid::sympathetic, 0.40f }, { pid::mechNoise, 0.45f },
            { pid::eqLow, 1.0f }, { pid::eqMid, 0.5f }, { pid::eqAir, 1.5f },
            { pid::compAmount, 0.30f }, { pid::drive, 0.15f }, { pid::chorusAmount, 0.10f },
            { pid::delayMix, 0.0f },
            { pid::reverbMix, 0.30f }, { pid::reverbSize, 0.50f }, { pid::reverbDecay, 2.2f },
            { pid::reverbTone, 0.45f }, { pid::reverbPredelay, 15.0f },
            { pid::padLevel, -60.0f } } },

        { "Ballad Grand", "Classic",
          "Full grand with a touch of delay. Verses and slow builds.",
          { { pid::model, 0 }, { pid::brightness, 0.15f }, { pid::hardness, 0.50f },
            { pid::decayTime, 1.1f }, { pid::detune, 5.0f }, { pid::sympathetic, 0.45f },
            { pid::dynamicRange, 24.0f },
            { pid::eqLow, 1.0f }, { pid::eqMid, -1.0f }, { pid::eqHigh, 1.5f }, { pid::eqAir, 3.0f },
            { pid::compAmount, 0.40f }, { pid::drive, 0.14f }, { pid::chorusAmount, 0.10f },
            { pid::delayMix, 0.16f }, { pid::delayDiv, 2 }, { pid::delayFeedback, 0.30f },
            { pid::delayTone, 0.45f }, { pid::delayPingPong, 0.75f },
            { pid::reverbMix, 0.35f }, { pid::reverbSize, 0.65f }, { pid::reverbDecay, 3.4f },
            { pid::reverbTone, 0.50f }, { pid::reverbPredelay, 25.0f }, { pid::shimmer, 0.05f },
            { pid::padLevel, -60.0f } } },

        { "Modern Worship Lead", "Modern",
          "Bright stage piano into a dotted eighth delay and a wide plate.",
          { { pid::model, 3 }, { pid::brightness, 0.30f }, { pid::hardness, 0.65f },
            { pid::decayTime, 1.05f }, { pid::detune, 6.0f }, { pid::sympathetic, 0.40f },
            { pid::dynamicRange, 22.0f },
            { pid::eqLow, 1.5f }, { pid::eqMid, -2.0f }, { pid::eqHigh, 2.5f }, { pid::eqAir, 4.5f },
            { pid::compAmount, 0.50f }, { pid::drive, 0.20f }, { pid::chorusAmount, 0.14f },
            { pid::delayMix, 0.30f }, { pid::delayDiv, 2 }, { pid::delayFeedback, 0.45f },
            { pid::delayTone, 0.50f }, { pid::delayPingPong, 0.85f },
            { pid::reverbMix, 0.38f }, { pid::reverbSize, 0.70f }, { pid::reverbDecay, 3.8f },
            { pid::reverbTone, 0.55f }, { pid::reverbPredelay, 28.0f }, { pid::shimmer, 0.10f },
            { pid::padLevel, -22.0f }, { pid::padAttack, 800.0f }, { pid::padRelease, 2200.0f } } },

        { "Ambient Bed", "Ambient",
          "Barely a piano any more. Hold a chord and let it move on its own.",
          { { pid::model, 2 }, { pid::brightness, -0.30f }, { pid::hardness, 0.12f },
            { pid::decayTime, 1.6f }, { pid::detune, 12.0f }, { pid::sympathetic, 0.80f },
            { pid::mechNoise, 0.25f }, { pid::dynamicRange, 36.0f }, { pid::pianoLevel, -4.0f },
            { pid::eqLow, -2.0f }, { pid::eqMid, -3.0f }, { pid::eqHigh, 1.0f }, { pid::eqAir, 5.0f },
            { pid::compAmount, 0.55f }, { pid::drive, 0.25f },
            { pid::chorusAmount, 0.50f }, { pid::chorusRate, 0.15f },
            { pid::delayMix, 0.40f }, { pid::delayDiv, 4 }, { pid::delayFeedback, 0.60f },
            { pid::delayTone, 0.35f }, { pid::delayPingPong, 0.95f },
            { pid::reverbMix, 0.65f }, { pid::reverbSize, 1.0f }, { pid::reverbDecay, 14.0f },
            { pid::reverbTone, 0.50f }, { pid::reverbPredelay, 80.0f }, { pid::shimmer, 0.60f },
            { pid::padLevel, -10.0f }, { pid::padTone, 800.0f }, { pid::padAttack, 3000.0f },
            { pid::padRelease, 7000.0f }, { pid::padDetune, 20.0f },
            { pid::width, 1.40f } } },

        { "Bright Pop Piano", "Live",
          "Tight, glassy and very present. Up-tempo songs.",
          { { pid::model, 3 }, { pid::brightness, 0.50f }, { pid::hardness, 0.85f },
            { pid::decayTime, 0.90f }, { pid::detune, 4.0f }, { pid::sympathetic, 0.25f },
            { pid::dynamicRange, 16.0f },
            { pid::eqLow, 2.0f }, { pid::eqMid, -1.5f }, { pid::eqHigh, 3.5f }, { pid::eqAir, 6.0f },
            { pid::compAmount, 0.60f }, { pid::compMix, 0.95f },
            { pid::drive, 0.25f }, { pid::driveTone, 0.65f }, { pid::chorusAmount, 0.10f },
            { pid::delayMix, 0.18f }, { pid::delayDiv, 6 }, { pid::delayFeedback, 0.25f },
            { pid::delayTone, 0.60f }, { pid::delayPingPong, 0.60f },
            { pid::reverbMix, 0.22f }, { pid::reverbSize, 0.50f }, { pid::reverbDecay, 1.8f },
            { pid::reverbTone, 0.65f }, { pid::reverbPredelay, 10.0f },
            { pid::padLevel, -60.0f }, { pid::outputGain, -3.0f } } },
    };

    return list;
}

void apply (AudioProcessorValueTreeState& apvts, int index)
{
    const auto& list = factory();

    if (! isPositiveAndBelow (index, (int) list.size()))
        return;

    // start from a known state so a preset never inherits stray knob positions
    for (const auto& id : allParameterIDs())
        if (auto* p = apvts.getParameter (id))
            p->setValueNotifyingHost (p->getDefaultValue());

    for (const auto& entry : list[(size_t) index].values)
        if (auto* p = apvts.getParameter (entry.id))
            p->setValueNotifyingHost (p->convertTo0to1 (entry.value));
}

int indexForName (const String& name)
{
    const auto& list = factory();

    for (int i = 0; i < (int) list.size(); ++i)
        if (list[(size_t) i].name.equalsIgnoreCase (name))
            return i;

    return -1;
}

} // namespace presets
