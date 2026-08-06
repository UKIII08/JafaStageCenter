#include "Presets.h"
#include "Parameters.h"

using namespace juce;

namespace presets
{

/*
    Eleven starting points rather than a catalogue. Every one of them is meant
    to be playable straight away without touching a knob.
*/
const std::vector<Preset>& factory()
{
    static const std::vector<Preset> list =
    {
        //======================================================== Classic =====
        { "Sunday Grand", "Classic",
          "Smooth concert grand in a warm room. The default.",
          { { pid::model, 0 }, { pid::tone, 0.0f }, { pid::attack, 0.30f },
            { pid::decayTime, 1.10f }, { pid::dynamicRange, 26.0f },
            { pid::eqLow, 1.0f }, { pid::eqHigh, 0.5f }, { pid::eqAir, 2.5f },
            { pid::compAmount, 0.28f }, { pid::drive, 0.10f }, { pid::chorusAmount, 0.06f },
            { pid::delayMix, 0.0f },
            { pid::reverbMix, 0.28f }, { pid::reverbSize, 0.55f }, { pid::reverbDecay, 3.0f },
            { pid::shimmer, 0.0f }, { pid::padLevel, -60.0f } } },

        { "Intimate Prayer", "Classic",
          "Soft, close and dark. Sits under a spoken voice without crowding it.",
          { { pid::model, 0 }, { pid::tone, -0.35f }, { pid::attack, 0.22f },
            { pid::decayTime, 1.0f }, { pid::dynamicRange, 32.0f },
            { pid::eqLow, 0.5f }, { pid::eqHigh, -1.5f }, { pid::eqAir, 1.0f },
            { pid::compAmount, 0.22f }, { pid::drive, 0.06f }, { pid::chorusAmount, 0.04f },
            { pid::delayMix, 0.0f },
            { pid::reverbMix, 0.20f }, { pid::reverbSize, 0.35f }, { pid::reverbDecay, 1.7f },
            { pid::shimmer, 0.0f }, { pid::padLevel, -60.0f } } },

        { "Ballad Grand", "Classic",
          "Full grand with a touch of delay. Verses and slow builds.",
          { { pid::model, 0 }, { pid::tone, 0.12f }, { pid::attack, 0.32f },
            { pid::decayTime, 1.15f }, { pid::dynamicRange, 24.0f },
            { pid::eqLow, 1.0f }, { pid::eqHigh, 1.0f }, { pid::eqAir, 3.0f },
            { pid::compAmount, 0.35f }, { pid::drive, 0.12f }, { pid::chorusAmount, 0.08f },
            { pid::delayMix, 0.14f }, { pid::delayDiv, 2 }, { pid::delayFeedback, 0.30f },
            { pid::reverbMix, 0.32f }, { pid::reverbSize, 0.60f }, { pid::reverbDecay, 3.4f },
            { pid::shimmer, 0.04f }, { pid::padLevel, -60.0f } } },

        { "Upright Chapel", "Classic",
          "Small warm upright, drier and boxier, with more of the action in it.",
          { { pid::model, 2 }, { pid::tone, 0.0f }, { pid::attack, 0.45f },
            { pid::decayTime, 1.0f }, { pid::dynamicRange, 26.0f },
            { pid::eqLow, 1.0f }, { pid::eqAir, 1.5f },
            { pid::compAmount, 0.28f }, { pid::drive, 0.12f }, { pid::chorusAmount, 0.08f },
            { pid::delayMix, 0.0f },
            { pid::reverbMix, 0.28f }, { pid::reverbSize, 0.50f }, { pid::reverbDecay, 2.2f },
            { pid::shimmer, 0.0f }, { pid::padLevel, -60.0f } } },

        //========================================================= Modern =====
        { "Modern Worship Lead", "Modern",
          "Bright grand into a dotted eighth delay and a wide plate.",
          { { pid::model, 1 }, { pid::tone, 0.25f }, { pid::attack, 0.42f },
            { pid::decayTime, 1.05f }, { pid::dynamicRange, 22.0f },
            { pid::eqLow, 1.5f }, { pid::eqHigh, 2.0f }, { pid::eqAir, 4.0f },
            { pid::compAmount, 0.45f }, { pid::drive, 0.18f }, { pid::chorusAmount, 0.12f },
            { pid::delayMix, 0.28f }, { pid::delayDiv, 2 }, { pid::delayFeedback, 0.44f },
            { pid::reverbMix, 0.34f }, { pid::reverbSize, 0.68f }, { pid::reverbDecay, 3.6f },
            { pid::shimmer, 0.08f },
            { pid::padLevel, -24.0f }, { pid::padAttack, 800.0f }, { pid::padRelease, 2200.0f } } },

        { "Arena Anthem", "Modern",
          "Compressed, forward and huge. The big chorus.",
          { { pid::model, 1 }, { pid::tone, 0.35f }, { pid::attack, 0.50f },
            { pid::decayTime, 1.10f }, { pid::dynamicRange, 20.0f },
            { pid::eqLow, 2.0f }, { pid::eqHigh, 2.5f }, { pid::eqAir, 5.0f },
            { pid::compAmount, 0.52f }, { pid::drive, 0.22f }, { pid::chorusAmount, 0.15f },
            { pid::delayMix, 0.30f }, { pid::delayDiv, 2 }, { pid::delayFeedback, 0.42f },
            { pid::reverbMix, 0.40f }, { pid::reverbSize, 0.75f }, { pid::reverbDecay, 4.5f },
            { pid::shimmer, 0.08f }, { pid::padLevel, -60.0f }, { pid::outputGain, -1.0f } } },

        { "Pad Underneath", "Modern",
          "Piano with a synth bed swelling on the same notes.",
          { { pid::model, 0 }, { pid::tone, 0.05f }, { pid::attack, 0.30f },
            { pid::decayTime, 1.10f }, { pid::dynamicRange, 25.0f },
            { pid::eqLow, 1.0f }, { pid::eqAir, 3.0f },
            { pid::compAmount, 0.32f }, { pid::drive, 0.12f }, { pid::chorusAmount, 0.10f },
            { pid::delayMix, 0.16f }, { pid::delayDiv, 2 }, { pid::delayFeedback, 0.34f },
            { pid::reverbMix, 0.32f }, { pid::reverbSize, 0.65f }, { pid::reverbDecay, 3.5f },
            { pid::shimmer, 0.10f },
            { pid::padLevel, -14.0f }, { pid::padTone, 1800.0f },
            { pid::padAttack, 900.0f }, { pid::padRelease, 2600.0f } } },

        //======================================================== Ambient =====
        { "Upper Room", "Ambient",
          "Felt hammers, long shimmer and a pad underneath. The quiet moment.",
          { { pid::model, 3 }, { pid::tone, -0.10f }, { pid::attack, 0.28f },
            { pid::decayTime, 1.20f }, { pid::dynamicRange, 30.0f },
            { pid::eqHigh, 0.5f }, { pid::eqAir, 3.0f },
            { pid::compAmount, 0.38f }, { pid::drive, 0.16f }, { pid::chorusAmount, 0.26f },
            { pid::delayMix, 0.26f }, { pid::delayDiv, 3 }, { pid::delayFeedback, 0.48f },
            { pid::reverbMix, 0.50f }, { pid::reverbSize, 0.88f }, { pid::reverbDecay, 8.0f },
            { pid::shimmer, 0.40f },
            { pid::padLevel, -20.0f }, { pid::padTone, 1200.0f },
            { pid::padAttack, 1200.0f }, { pid::padRelease, 3500.0f } } },

        { "Felt & Air", "Ambient",
          "Cloth over the hammers and a slow wobble. Almost no attack left.",
          { { pid::model, 3 }, { pid::tone, -0.30f }, { pid::attack, 0.20f },
            { pid::decayTime, 0.95f }, { pid::dynamicRange, 28.0f },
            { pid::eqLow, 1.5f }, { pid::eqHigh, -2.0f }, { pid::eqAir, 0.5f },
            { pid::compAmount, 0.40f }, { pid::drive, 0.28f }, { pid::chorusAmount, 0.30f },
            { pid::delayMix, 0.12f }, { pid::delayDiv, 3 }, { pid::delayFeedback, 0.30f },
            { pid::reverbMix, 0.34f }, { pid::reverbSize, 0.50f }, { pid::reverbDecay, 2.6f },
            { pid::shimmer, 0.05f }, { pid::padLevel, -60.0f } } },

        { "Ambient Bed", "Ambient",
          "Hold a chord and let it move on its own.",
          { { pid::model, 3 }, { pid::tone, -0.25f }, { pid::attack, 0.15f },
            { pid::decayTime, 1.50f }, { pid::dynamicRange, 34.0f }, { pid::pianoLevel, -3.0f },
            { pid::eqLow, -1.0f }, { pid::eqHigh, 0.5f }, { pid::eqAir, 4.0f },
            { pid::compAmount, 0.50f }, { pid::drive, 0.20f }, { pid::chorusAmount, 0.45f },
            { pid::delayMix, 0.36f }, { pid::delayDiv, 4 }, { pid::delayFeedback, 0.58f },
            { pid::reverbMix, 0.60f }, { pid::reverbSize, 1.0f }, { pid::reverbDecay, 12.0f },
            { pid::shimmer, 0.55f },
            { pid::padLevel, -12.0f }, { pid::padTone, 900.0f },
            { pid::padAttack, 2500.0f }, { pid::padRelease, 6000.0f },
            { pid::width, 1.30f } } },

        //=========================================================== Live =====
        { "Stage Clean", "Live",
          "Dry and forward for playing through a PA. Add the house reverb yourself.",
          { { pid::model, 1 }, { pid::tone, 0.15f }, { pid::attack, 0.40f },
            { pid::decayTime, 1.0f }, { pid::dynamicRange, 24.0f },
            { pid::eqLow, 0.5f }, { pid::eqHigh, 1.5f }, { pid::eqAir, 3.0f },
            { pid::compAmount, 0.30f }, { pid::drive, 0.05f }, { pid::chorusAmount, 0.0f },
            { pid::delayMix, 0.0f },
            { pid::reverbMix, 0.08f }, { pid::reverbSize, 0.40f }, { pid::reverbDecay, 1.2f },
            { pid::shimmer, 0.0f }, { pid::padLevel, -60.0f } } },
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
