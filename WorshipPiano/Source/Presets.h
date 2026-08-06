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
}
