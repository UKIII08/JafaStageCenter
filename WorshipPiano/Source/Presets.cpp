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
          { { pid::reverbMachine, 1 }, { pid::tone, 0.0f }, { pid::attack, 0.30f },
            { pid::decayTime, 1.10f }, { pid::dynamicRange, 26.0f },
            { pid::eqLow, 1.0f }, { pid::eqHigh, 0.5f }, { pid::eqAir, 2.5f },
            { pid::compAmount, 0.28f }, { pid::drive, 0.10f }, { pid::chorusAmount, 0.06f },
            { pid::delayMix, 0.0f },
            { pid::reverbMix, 0.28f }, { pid::reverbSize, 0.55f }, { pid::reverbDecay, 3.0f },
            { pid::shimmer, 0.0f }, { pid::padLevel, -60.0f } } },

        { "Intimate Prayer", "Classic",
          "Soft, close and dark. Sits under a spoken voice without crowding it.",
          { { pid::reverbMachine, 0 }, { pid::tone, -0.35f }, { pid::attack, 0.22f },
            { pid::decayTime, 1.0f }, { pid::dynamicRange, 32.0f },
            { pid::eqLow, 0.5f }, { pid::eqHigh, -1.5f }, { pid::eqAir, 1.0f },
            { pid::compAmount, 0.22f }, { pid::drive, 0.06f }, { pid::chorusAmount, 0.04f },
            { pid::delayMix, 0.0f },
            { pid::reverbMix, 0.20f }, { pid::reverbSize, 0.35f }, { pid::reverbDecay, 1.7f },
            { pid::shimmer, 0.0f }, { pid::padLevel, -60.0f } } },

        { "Ballad Grand", "Classic",
          "Full grand with a touch of delay. Verses and slow builds.",
          { { pid::reverbMachine, 1 }, { pid::tone, 0.12f }, { pid::attack, 0.32f },
            { pid::decayTime, 1.15f }, { pid::dynamicRange, 24.0f },
            { pid::eqLow, 1.0f }, { pid::eqHigh, 1.0f }, { pid::eqAir, 3.0f },
            { pid::compAmount, 0.35f }, { pid::drive, 0.12f }, { pid::chorusAmount, 0.08f },
            { pid::delayMix, 0.14f }, { pid::delayDiv, 2 }, { pid::delayFeedback, 0.30f },
            { pid::reverbMix, 0.32f }, { pid::reverbSize, 0.60f }, { pid::reverbDecay, 3.4f },
            { pid::shimmer, 0.04f }, { pid::padLevel, -60.0f } } },

        { "Upright Chapel", "Classic",
          "Small warm upright, drier and boxier, with more of the action in it.",
          { { pid::reverbMachine, 0 }, { pid::tone, 0.0f }, { pid::attack, 0.45f },
            { pid::decayTime, 1.0f }, { pid::dynamicRange, 26.0f },
            { pid::eqLow, 1.0f }, { pid::eqAir, 1.5f },
            { pid::compAmount, 0.28f }, { pid::drive, 0.12f }, { pid::chorusAmount, 0.08f },
            { pid::delayMix, 0.0f },
            { pid::reverbMix, 0.28f }, { pid::reverbSize, 0.50f }, { pid::reverbDecay, 2.2f },
            { pid::shimmer, 0.0f }, { pid::padLevel, -60.0f } } },

        //========================================================= Modern =====
        { "Modern Worship Lead", "Modern",
          "Bright grand into a dotted eighth delay and a wide plate.",
          { { pid::reverbMachine, 2 }, { pid::tone, 0.25f }, { pid::attack, 0.42f },
            { pid::decayTime, 1.05f }, { pid::dynamicRange, 22.0f },
            { pid::eqLow, 1.5f }, { pid::eqHigh, 2.0f }, { pid::eqAir, 4.0f },
            { pid::compAmount, 0.45f }, { pid::drive, 0.18f }, { pid::chorusAmount, 0.12f },
            { pid::delayMix, 0.28f }, { pid::delayDiv, 2 }, { pid::delayFeedback, 0.44f },
            { pid::reverbDuck, 0.2f }, { pid::reverbMix, 0.34f }, { pid::reverbSize, 0.68f }, { pid::reverbDecay, 3.6f },
            { pid::shimmer, 0.08f },
            { pid::tackOn, 1 }, { pid::tackAmount, 0.22f },
            { pid::padType, 2 }, { pid::padLevel, -20.0f },
            { pid::padAttack, 800.0f }, { pid::padRelease, 2200.0f } } },

        { "Arena Anthem", "Modern",
          "Compressed, forward and huge. The big chorus.",
          { { pid::reverbMachine, 2 }, { pid::tone, 0.35f }, { pid::attack, 0.50f },
            { pid::decayTime, 1.10f }, { pid::dynamicRange, 20.0f },
            { pid::eqLow, 2.0f }, { pid::eqHigh, 2.5f }, { pid::eqAir, 5.0f },
            { pid::compAmount, 0.52f }, { pid::drive, 0.22f }, { pid::chorusAmount, 0.15f },
            { pid::delayMix, 0.30f }, { pid::delayDiv, 2 }, { pid::delayFeedback, 0.42f },
            { pid::reverbDuck, 0.25f }, { pid::reverbMix, 0.40f }, { pid::reverbSize, 0.75f }, { pid::reverbDecay, 4.5f },
            { pid::shimmer, 0.08f }, { pid::padLevel, -60.0f },
            { pid::tackOn, 1 }, { pid::tackAmount, 0.30f }, { pid::outputGain, -1.0f } } },

        { "Pad Underneath", "Modern",
          "Piano with a synth bed swelling on the same notes.",
          { { pid::reverbMachine, 1 }, { pid::tone, 0.05f }, { pid::attack, 0.30f },
            { pid::decayTime, 1.10f }, { pid::dynamicRange, 25.0f },
            { pid::eqLow, 1.0f }, { pid::eqAir, 3.0f },
            { pid::compAmount, 0.32f }, { pid::drive, 0.12f }, { pid::chorusAmount, 0.10f },
            { pid::delayMix, 0.16f }, { pid::delayDiv, 2 }, { pid::delayFeedback, 0.34f },
            { pid::reverbMix, 0.32f }, { pid::reverbSize, 0.65f }, { pid::reverbDecay, 3.5f },
            { pid::shimmer, 0.10f },
            { pid::padType, 0 }, { pid::padLevel, -15.0f }, { pid::padTone, 1800.0f },
            { pid::padAttack, 900.0f }, { pid::padRelease, 2600.0f } } },

        //======================================================== Ambient =====
        { "Upper Room", "Ambient",
          "Felt hammers, long shimmer and a pad underneath. The quiet moment.",
          { { pid::reverbMachine, 5 }, { pid::tone, -0.10f }, { pid::attack, 0.28f },
            { pid::decayTime, 1.20f }, { pid::dynamicRange, 30.0f },
            { pid::eqHigh, 0.5f }, { pid::eqAir, 3.0f },
            { pid::compAmount, 0.38f }, { pid::drive, 0.16f }, { pid::chorusAmount, 0.26f },
            { pid::delayMix, 0.26f }, { pid::delayDiv, 3 }, { pid::delayFeedback, 0.48f },
            { pid::reverbMix, 0.50f }, { pid::reverbSize, 0.88f }, { pid::reverbDecay, 8.0f },
            { pid::shimmer, 0.40f },
            { pid::padType, 1 }, { pid::padLevel, -15.0f }, { pid::padTone, 1200.0f },
            { pid::padAttack, 1200.0f }, { pid::padRelease, 3500.0f } } },

        { "Felt & Air", "Ambient",
          "Cloth over the hammers and a slow wobble. Almost no attack left.",
          { { pid::reverbMachine, 4 }, { pid::tone, -0.30f }, { pid::attack, 0.20f },
            { pid::decayTime, 0.95f }, { pid::dynamicRange, 28.0f },
            { pid::eqLow, 1.5f }, { pid::eqHigh, -2.0f }, { pid::eqAir, 0.5f },
            { pid::compAmount, 0.40f }, { pid::drive, 0.28f }, { pid::chorusAmount, 0.30f },
            { pid::delayMix, 0.12f }, { pid::delayDiv, 3 }, { pid::delayFeedback, 0.30f },
            { pid::reverbMix, 0.34f }, { pid::reverbSize, 0.50f }, { pid::reverbDecay, 2.6f },
            { pid::shimmer, 0.05f }, { pid::padLevel, -60.0f } } },

        { "Ambient Bed", "Ambient",
          "Hold a chord and let it move on its own.",
          { { pid::reverbMachine, 3 }, { pid::tone, -0.25f }, { pid::attack, 0.15f },
            { pid::decayTime, 1.50f }, { pid::dynamicRange, 34.0f }, { pid::pianoLevel, -3.0f },
            { pid::eqLow, -1.0f }, { pid::eqHigh, 0.5f }, { pid::eqAir, 4.0f },
            { pid::compAmount, 0.50f }, { pid::drive, 0.20f }, { pid::chorusAmount, 0.45f },
            { pid::delayMix, 0.36f }, { pid::delayDiv, 4 }, { pid::delayFeedback, 0.58f },
            { pid::reverbMix, 0.60f }, { pid::reverbSize, 1.0f }, { pid::reverbDecay, 12.0f },
            { pid::shimmer, 0.55f },
            { pid::padType, 3 }, { pid::padLevel, -11.0f }, { pid::padTone, 900.0f },
            { pid::padAttack, 2500.0f }, { pid::padRelease, 6000.0f },
            { pid::width, 1.30f }, { pid::outputGain, -1.5f } } },

        //=========================================================== Soak =====
        { "Soaking Grand", "Soak",
          "Piano with an ambient bed swelling up behind it. Start here for soaking.",
          { { pid::reverbMachine, 4 }, { pid::tone, -0.05f },
            { pid::attack, 0.26f }, { pid::decayTime, 1.25f }, { pid::dynamicRange, 28.0f },
            { pid::eqLow, 1.0f }, { pid::eqAir, 3.0f },
            { pid::compAmount, 0.34f }, { pid::drive, 0.12f }, { pid::chorusAmount, 0.18f },
            { pid::delayMix, 0.18f }, { pid::delayDiv, 2 }, { pid::delayFeedback, 0.40f },
            { pid::reverbMix, 0.48f }, { pid::reverbSize, 0.85f }, { pid::reverbDecay, 8.0f },
            { pid::shimmer, 0.22f }, { pid::reverbDuck, 0.25f },
            { pid::padType, 1 }, { pid::padLevel, -14.0f }, { pid::padTone, 1300.0f },
            { pid::padAttack, 1400.0f }, { pid::padRelease, 4000.0f },
            { pid::soak, 0.35f } } },

        { "Soaking Cloud", "Soak",
          "Everything blurred into one slow moving cloud. Octave and fifth on top.",
          { { pid::reverbMachine, 3 }, { pid::tone, -0.15f },
            { pid::attack, 0.20f }, { pid::decayTime, 1.40f }, { pid::dynamicRange, 30.0f },
            { pid::eqLow, -0.5f }, { pid::eqAir, 4.0f },
            { pid::compAmount, 0.42f }, { pid::drive, 0.16f }, { pid::chorusAmount, 0.32f },
            { pid::delayMix, 0.26f }, { pid::delayDiv, 3 }, { pid::delayFeedback, 0.50f },
            { pid::reverbMix, 0.58f }, { pid::reverbSize, 1.0f }, { pid::reverbDecay, 16.0f },
            { pid::shimmer, 0.45f }, { pid::shimmerMode, 1 }, { pid::reverbDuck, 0.20f },
            { pid::padType, 4 }, { pid::padLevel, -11.0f }, { pid::padTone, 1000.0f },
            { pid::padAttack, 2200.0f }, { pid::padRelease, 5500.0f },
            { pid::soak, 0.50f }, { pid::width, 1.25f }, { pid::outputGain, -1.0f } } },

        { "Prayer Room", "Soak",
          "Felt piano over a slow bloom, ducking so the notes stay readable.",
          { { pid::reverbMachine, 4 }, { pid::tone, -0.20f },
            { pid::attack, 0.18f }, { pid::decayTime, 1.20f }, { pid::dynamicRange, 32.0f },
            { pid::eqLow, 1.0f }, { pid::eqHigh, -1.0f }, { pid::eqAir, 2.0f },
            { pid::compAmount, 0.30f }, { pid::drive, 0.10f }, { pid::chorusAmount, 0.20f },
            { pid::delayMix, 0.14f }, { pid::delayDiv, 3 }, { pid::delayFeedback, 0.36f },
            { pid::reverbMix, 0.46f }, { pid::reverbSize, 0.80f }, { pid::reverbDecay, 9.0f },
            { pid::shimmer, 0.18f }, { pid::reverbDuck, 0.35f },
            { pid::padType, 1 }, { pid::padLevel, -12.0f }, { pid::padTone, 950.0f },
            { pid::padAttack, 1800.0f }, { pid::padRelease, 5000.0f },
            { pid::soak, 0.30f } } },

        { "Infinite Wash", "Soak",
          "Hold a chord, hit FREEZE, and play over the top of it forever.",
          { { pid::reverbMachine, 5 }, { pid::tone, -0.10f },
            { pid::attack, 0.16f }, { pid::decayTime, 1.60f }, { pid::dynamicRange, 34.0f },
            { pid::pianoLevel, -2.0f },
            { pid::eqLow, -1.5f }, { pid::eqAir, 5.0f },
            { pid::compAmount, 0.48f }, { pid::drive, 0.18f }, { pid::chorusAmount, 0.40f },
            { pid::delayMix, 0.32f }, { pid::delayDiv, 4 }, { pid::delayFeedback, 0.55f },
            { pid::reverbMix, 0.62f }, { pid::reverbSize, 1.0f }, { pid::reverbDecay, 24.0f },
            { pid::shimmer, 0.60f }, { pid::shimmerMode, 3 }, { pid::reverbDuck, 0.15f },
            { pid::padType, 3 }, { pid::padLevel, -9.0f }, { pid::padTone, 900.0f },
            { pid::padAttack, 2600.0f }, { pid::padRelease, 6500.0f },
            { pid::soak, 0.62f }, { pid::width, 1.35f }, { pid::outputGain, -2.5f } } },

        { "Reverse Swell", "Soak",
          "Every phrase blooms into itself backwards. Play sparsely and let it breathe.",
          { { pid::reverbMachine, 4 }, { pid::tone, -0.15f },
            { pid::attack, 0.18f }, { pid::decayTime, 1.30f }, { pid::dynamicRange, 30.0f },
            { pid::eqLow, 0.5f }, { pid::eqAir, 3.5f },
            { pid::compAmount, 0.36f }, { pid::drive, 0.14f }, { pid::chorusAmount, 0.24f },
            { pid::delayMix, 0.10f }, { pid::delayDiv, 3 }, { pid::delayFeedback, 0.34f },
            { pid::reverseMix, 0.55f }, { pid::reverseTime, 1 },
            { pid::reverbMix, 0.44f }, { pid::reverbSize, 0.82f }, { pid::reverbDecay, 7.0f },
            { pid::shimmer, 0.20f }, { pid::reverbDuck, 0.20f },
            { pid::padType, 4 }, { pid::padLevel, -16.0f }, { pid::padTone, 1100.0f },
            { pid::padAttack, 1600.0f }, { pid::padRelease, 4500.0f },
            { pid::soak, 0.30f }, { pid::outputGain, -1.5f } } },

        //=========================================================== Live =====
        { "Stage Clean", "Live",
          "Dry and forward for playing through a PA. Add the house reverb yourself.",
          { { pid::reverbMachine, 0 }, { pid::tone, 0.15f }, { pid::attack, 0.40f },
            { pid::decayTime, 1.0f }, { pid::dynamicRange, 24.0f },
            { pid::eqLow, 0.5f }, { pid::eqHigh, 1.5f }, { pid::eqAir, 3.0f },
            { pid::compAmount, 0.30f }, { pid::drive, 0.05f }, { pid::chorusAmount, 0.0f },
            { pid::delayMix, 0.0f },
            { pid::reverbDuck, 0.15f }, { pid::reverbMix, 0.08f }, { pid::reverbSize, 0.40f }, { pid::reverbDecay, 1.2f },
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

//==============================================================================
String sanitiseName (const String& name)
{
    auto cleaned = File::createLegalFileName (name.trim());

    // a leading dot hides the file on every unix-like system, and a trailing
    // dot is not a legal file name on Windows
    while (cleaned.startsWithChar ('.') || cleaned.startsWithChar (' '))
        cleaned = cleaned.substring (1);

    while (cleaned.endsWithChar ('.') || cleaned.endsWithChar (' '))
        cleaned = cleaned.dropLastCharacters (1);

    return cleaned.substring (0, 64);
}

File userPresetDirectory()
{
    auto dir = File::getSpecialLocation (File::userApplicationDataDirectory)
                   .getChildFile ("Jafa Stage")
                   .getChildFile ("Worship Piano")
                   .getChildFile ("Presets");

    if (! dir.exists())
        dir.createDirectory();

    return dir;
}

StringArray userPresetNames()
{
    StringArray names;

    for (const auto& f : userPresetDirectory().findChildFiles (File::findFiles, false, "*.wppreset"))
        names.add (f.getFileNameWithoutExtension());

    names.sortNatural();
    return names;
}

String saveUser (AudioProcessorValueTreeState& apvts, const String& name, const String& libraryPath)
{
    const auto cleaned = sanitiseName (name);

    if (cleaned.isEmpty())
        return "Podaj nazwe presetu.";

    XmlElement xml ("WorshipPianoPreset");
    xml.setAttribute ("name", cleaned);

    // deliberately not written when empty, so "no library" and "the library this
    // was built on" stay two different things a preset can say
    if (libraryPath.isNotEmpty())
        xml.setAttribute ("libraryPath", libraryPath);

    for (const auto& id : allParameterIDs())
        if (auto* p = apvts.getParameter (id))
            xml.setAttribute (id, p->convertFrom0to1 (p->getValue()));

    auto file = userPresetDirectory().getChildFile (cleaned + ".wppreset");

    if (! xml.writeTo (file))
        return "Nie udalo sie zapisac do: " + file.getFullPathName();

    return {};
}

bool applyUser (AudioProcessorValueTreeState& apvts, const String& name, String* libraryPathOut)
{
    if (libraryPathOut != nullptr)
        libraryPathOut->clear();

    auto file = userPresetDirectory().getChildFile (sanitiseName (name) + ".wppreset");

    if (! file.existsAsFile())
        return false;

    auto xml = parseXML (file);

    if (xml == nullptr || ! xml->hasTagName ("WorshipPianoPreset"))
        return false;

    if (libraryPathOut != nullptr)
        *libraryPathOut = xml->getStringAttribute ("libraryPath");

    // same as the factory path: start from defaults so a preset saved by an
    // older build cannot leave a stray knob behind
    for (const auto& id : allParameterIDs())
        if (auto* p = apvts.getParameter (id))
            p->setValueNotifyingHost (p->getDefaultValue());

    for (const auto& id : allParameterIDs())
        if (auto* p = apvts.getParameter (id))
            if (xml->hasAttribute (id))
                p->setValueNotifyingHost (p->convertTo0to1 ((float) xml->getDoubleAttribute (id)));

    return true;
}

bool deleteUser (const String& name)
{
    return userPresetDirectory().getChildFile (sanitiseName (name) + ".wppreset").deleteFile();
}



//==============================================================================
namespace
{
    File favouritesFile()
    {
        return userPresetDirectory().getParentDirectory().getChildFile ("favourites.txt");
    }

    File viewFile()
    {
        return userPresetDirectory().getParentDirectory().getChildFile ("view.txt");
    }
}

bool presetListVisible()
{
    auto file = viewFile();

    // shown until somebody says otherwise: a fresh install that hid its own
    // preset list would look broken
    return ! file.existsAsFile() || ! file.loadFileAsString().trim().equalsIgnoreCase ("hidden");
}

void setPresetListVisible (bool shouldBeVisible)
{
    viewFile().replaceWithText (shouldBeVisible ? "shown" : "hidden");
}

StringArray favourites()
{
    StringArray names;
    auto file = favouritesFile();

    if (file.existsAsFile())
        names.addLines (file.loadFileAsString());

    names.removeEmptyStrings();
    names.removeDuplicates (true);

    // a preset that no longer exists must not hold a slot hostage
    for (int i = names.size(); --i >= 0;)
        if (indexForName (names[i]) < 0 && ! userPresetNames().contains (names[i]))
            names.remove (i);

    while (names.size() > maxFavourites)
        names.remove (names.size() - 1);

    return names;
}

void setFavourite (const String& name, bool shouldBeFavourite)
{
    if (name.isEmpty())
        return;

    auto names = favourites();
    const int existing = names.indexOf (name);

    if (shouldBeFavourite)
    {
        if (existing >= 0)
            return;

        // full board: the oldest star makes way, so starring never silently
        // does nothing
        if (names.size() >= maxFavourites)
            names.remove (0);

        names.add (name);
    }
    else if (existing >= 0)
    {
        names.remove (existing);
    }

    favouritesFile().replaceWithText (names.joinIntoString ("\n"));
}

bool isFavourite (const String& name)
{
    return favourites().contains (name);
}

} // namespace presets
