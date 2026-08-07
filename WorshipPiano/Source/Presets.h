#pragma once

#include <juce_audio_processors/juce_audio_processors.h>
#include <vector>

namespace presets
{
    struct Entry
    {
        const char* id;
        float value;
    };

    struct Preset
    {
        juce::String name;
        juce::String category;
        juce::String blurb;
        std::vector<Entry> values;
    };

    const std::vector<Preset>& factory();

    /** Resets every parameter to its default, then applies the preset. */
    void apply (juce::AudioProcessorValueTreeState& apvts, int index);

    int indexForName (const juce::String& name);

    //==========================================================================
    /*  User presets. Stored one XML file per preset next to the plugin's own
        settings, so they survive a reinstall and can be copied to another
        machine - a laptop that plays a Sunday service should not keep its
        sounds only inside one host's project file.
    */
    juce::File userPresetDirectory();

    /** Names of the user's own presets, sorted, refreshed from disk. */
    juce::StringArray userPresetNames();

    /*  A preset can carry the sample library it was built on. Two songs in one
        set often want two different pianos - a felt one under a prayer and a
        bright grand under the last chorus - and having to go and find the folder
        by hand between them is not something anybody does on a stage.

        An empty libraryPath saves the preset without one, and such a preset
        leaves whatever is loaded alone.

        @returns an error message, or empty on success.
    */
    juce::String saveUser (juce::AudioProcessorValueTreeState& apvts, const juce::String& name,
                           const juce::String& libraryPath = {});

    /** @param libraryPathOut  receives the preset's library, empty when it has none. */
    bool applyUser (juce::AudioProcessorValueTreeState& apvts, const juce::String& name,
                    juce::String* libraryPathOut = nullptr);

    bool deleteUser (const juce::String& name);

    /** Strips what a file name cannot hold, so a preset name is always usable. */
    juce::String sanitiseName (const juce::String& name);

    //==========================================================================
    /*  Quick access. Nobody hunts a list of twenty presets between two songs -
        a handful get starred and land on buttons that are one click away.
        Stored next to the user presets, so the choice follows the machine
        rather than a single project.
    */
    juce::StringArray favourites();
    void setFavourite (const juce::String& name, bool shouldBeFavourite);
    bool isFavourite (const juce::String& name);

    static constexpr int maxFavourites = 6;

    //==========================================================================
    /*  Whether the LIVE page shows the full preset list at all. Playing a set
        means reaching for the same handful of sounds, and the list is mostly
        something to knock with an elbow; folding it away leaves the quick bar
        as the only way in - and gives the width to the knobs.

        Kept on disk next to the favourites rather than in the project, because
        it describes the machine on the stage, not one song.
    */
    bool presetListVisible();
    void setPresetListVisible (bool shouldBeVisible);
}
