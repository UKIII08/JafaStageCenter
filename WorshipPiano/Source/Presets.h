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

    /** @returns an error message, or empty on success. */
    juce::String saveUser (juce::AudioProcessorValueTreeState& apvts, const juce::String& name);

    bool applyUser (juce::AudioProcessorValueTreeState& apvts, const juce::String& name);
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
}
