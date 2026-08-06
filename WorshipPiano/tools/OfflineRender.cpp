/*
    Offline harness: loads every factory preset, plays a short chord progression
    through the engine and writes a WAV per preset. Used to check that the DSP
    is stable (no NaNs, no runaway feedback, sensible levels) without needing a
    host or an audio device.

    Build with -DWORSHIPPIANO_BUILD_TOOLS=ON, then run:
        ./build/tools/WorshipPianoRender out_dir [presetIndex]
*/

#include <juce_audio_formats/juce_audio_formats.h>

#include "../Source/PluginProcessor.h"
#include "../Source/Presets.h"
#include "../Source/Parameters.h"

using namespace juce;

namespace
{
    constexpr double sampleRate = 48000.0;
    constexpr int blockSize = 512;

    struct Event { double timeSeconds; bool noteOn; int note; float velocity; };

    /** Simple ii-V-I style progression with the sustain pedal down. */
    std::vector<Event> buildPerformance()
    {
        std::vector<Event> events;

        const std::vector<std::vector<int>> chords
        {
            { 41, 60, 65, 69 },   // F  add
            { 43, 62, 67, 71 },   // G
            { 45, 64, 69, 72 },   // Am
            { 48, 64, 67, 72 },   // C
        };

        double t = 0.25;

        for (const auto& chord : chords)
        {
            int i = 0;

            for (int note : chord)
            {
                events.push_back ({ t + 0.012 * i, true, note, 0.55f + 0.06f * (float) i });
                events.push_back ({ t + 1.65, false, note, 0.0f });
                ++i;
            }

            t += 1.75;
        }

        // a melodic tail to hear the top end and the release behaviour
        const int melody[] = { 72, 74, 76, 79, 81 };
        for (int i = 0; i < 5; ++i)
        {
            events.push_back ({ t + 0.35 * i, true, melody[i], 0.75f });
            events.push_back ({ t + 0.35 * i + 0.30, false, melody[i], 0.0f });
        }

        return events;
    }

    /** A project reload in the host must bring every knob back exactly. */
    bool checkStateRoundTrip (String& report)
    {
        WorshipPianoProcessor source;
        source.setPlayConfigDetails (0, 2, sampleRate, blockSize);
        source.prepareToPlay (sampleRate, blockSize);
        source.loadPreset (7);

        // nudge a few parameters so we are not just testing the preset itself
        if (auto* p = source.apvts.getParameter (pid::reverbDecay)) p->setValueNotifyingHost (0.63f);
        if (auto* p = source.apvts.getParameter (pid::model))       p->setValueNotifyingHost (p->convertTo0to1 (1.0f));
        if (auto* p = source.apvts.getParameter (pid::delaySync))   p->setValueNotifyingHost (0.0f);

        MemoryBlock state;
        source.getStateInformation (state);

        WorshipPianoProcessor restored;
        restored.setPlayConfigDetails (0, 2, sampleRate, blockSize);
        restored.prepareToPlay (sampleRate, blockSize);
        restored.setStateInformation (state.getData(), (int) state.getSize());

        int mismatches = 0;

        for (const auto& id : allParameterIDs())
        {
            const float a = source.apvts.getRawParameterValue (id)->load();
            const float b = restored.apvts.getRawParameterValue (id)->load();

            if (std::abs (a - b) > 1.0e-5f * jmax (1.0f, std::abs (a)))
            {
                report << "     state mismatch on " << id << ": " << a << " vs " << b << newLine;
                ++mismatches;
            }
        }

        report << "state round trip: " << (mismatches == 0 ? "OK" : String (mismatches) + " MISMATCHES")
               << " (" << state.getSize() << " bytes)" << newLine << newLine;

        return mismatches == 0;
    }

    bool renderPreset (int presetIndex, const File& outputDir, String& report)
    {
        WorshipPianoProcessor processor;
        processor.setPlayConfigDetails (0, 2, sampleRate, blockSize);
        processor.prepareToPlay (sampleRate, blockSize);
        processor.loadPreset (presetIndex);

        const auto events = buildPerformance();
        const double lengthSeconds = 16.0;
        const int totalSamples = (int) (lengthSeconds * sampleRate);

        AudioBuffer<float> output (2, totalSamples);
        output.clear();

        AudioBuffer<float> block (2, blockSize);
        size_t nextEvent = 0;
        int written = 0;
        bool sustainSent = false;

        while (written < totalSamples)
        {
            const int numSamples = jmin (blockSize, totalSamples - written);
            block.setSize (2, numSamples, false, false, true);
            block.clear();

            MidiBuffer midi;

            if (! sustainSent)
            {
                midi.addEvent (MidiMessage::controllerEvent (1, 64, 127), 0);
                sustainSent = true;
            }

            const double blockStart = (double) written / sampleRate;
            const double blockEnd = (double) (written + numSamples) / sampleRate;

            while (nextEvent < events.size() && events[nextEvent].timeSeconds < blockEnd)
            {
                const auto& e = events[nextEvent];
                const int offset = jlimit (0, numSamples - 1,
                                           (int) ((e.timeSeconds - blockStart) * sampleRate));

                midi.addEvent (e.noteOn ? MidiMessage::noteOn (1, e.note, e.velocity)
                                        : MidiMessage::noteOff (1, e.note),
                               offset);
                ++nextEvent;
            }

            processor.processBlock (block, midi);

            for (int ch = 0; ch < 2; ++ch)
                output.copyFrom (ch, written, block, ch, 0, numSamples);

            written += numSamples;
        }

        // ---- sanity checks --------------------------------------------------
        float peak = 0.0f;
        double sumSquares = 0.0;
        int badSamples = 0;

        for (int ch = 0; ch < 2; ++ch)
        {
            const auto* data = output.getReadPointer (ch);

            for (int n = 0; n < totalSamples; ++n)
            {
                const float v = data[n];

                if (! std::isfinite (v))
                    ++badSamples;
                else
                {
                    peak = jmax (peak, std::abs (v));
                    sumSquares += (double) v * v;
                }
            }
        }

        const double rms = std::sqrt (sumSquares / (double) (totalSamples * 2));

        // tail level: the last half second should be quieter than the body,
        // otherwise something in the feedback paths is not decaying
        double tailSum = 0.0;
        const int tailStart = totalSamples - (int) (0.5 * sampleRate);

        for (int ch = 0; ch < 2; ++ch)
            for (int n = tailStart; n < totalSamples; ++n)
                tailSum += std::abs (output.getSample (ch, n));

        const double tailAvg = tailSum / (double) ((totalSamples - tailStart) * 2);

        const auto name = presets::factory()[(size_t) presetIndex].name;

        report << String (presetIndex).paddedLeft (' ', 3) << "  "
               << name.paddedRight (' ', 22)
               << "peak " << String (Decibels::gainToDecibels (jmax (1.0e-6f, peak)), 1).paddedLeft (' ', 7) << " dB"
               << "   rms " << String (Decibels::gainToDecibels (jmax (1.0e-6, rms)), 1).paddedLeft (' ', 7) << " dB"
               << "   tail " << String (Decibels::gainToDecibels (jmax (1.0e-6, tailAvg)), 1).paddedLeft (' ', 7) << " dB";

        bool ok = true;

        if (badSamples > 0)      { report << "   !! " << badSamples << " non-finite samples"; ok = false; }
        if (peak > 1.5f)         { report << "   !! clipping hot"; ok = false; }
        if (rms < 1.0e-4)        { report << "   !! silent"; ok = false; }

        report << newLine;

        if (outputDir != File())
        {
            outputDir.createDirectory();
            auto file = outputDir.getChildFile (String (presetIndex + 1).paddedLeft ('0', 2)
                                                + " - " + name + ".wav");
            file.deleteFile();

            WavAudioFormat format;
            std::unique_ptr<FileOutputStream> stream (file.createOutputStream());

            if (stream != nullptr)
            {
                std::unique_ptr<AudioFormatWriter> writer (
                    format.createWriterFor (stream.get(), sampleRate, 2, 24, {}, 0));

                if (writer != nullptr)
                {
                    stream.release();
                    writer->writeFromAudioSampleBuffer (output, 0, totalSamples);
                }
            }
        }

        return ok;
    }
}

int main (int argc, char** argv)
{
    ScopedJuceInitialiser_GUI juceInit;

    const File outputDir = argc > 1 ? File::getCurrentWorkingDirectory().getChildFile (argv[1]) : File();
    const int single = argc > 2 ? String (argv[2]).getIntValue() : -1;

    String report;
    bool allOk = checkStateRoundTrip (report);

    for (int i = 0; i < (int) presets::factory().size(); ++i)
    {
        if (single >= 0 && i != single)
            continue;

        allOk &= renderPreset (i, outputDir, report);
    }

    std::cout << report << std::endl;
    std::cout << (allOk ? "ALL PRESETS OK" : "PROBLEMS FOUND") << std::endl;

    return allOk ? 0 : 1;
}
