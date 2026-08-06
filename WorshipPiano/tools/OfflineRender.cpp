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
#include "../Source/dsp/SampleLibrary.h"

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

    /** One sustained note, for looking at the spectrum without chord clutter. */
    void renderSingleNote (int presetIndex, int midiNote, float velocity, const File& file)
    {
        WorshipPianoProcessor processor;
        processor.setPlayConfigDetails (0, 2, sampleRate, blockSize);
        processor.prepareToPlay (sampleRate, blockSize);
        processor.loadPreset (presetIndex);

        // dry, so the analysis sees the engine and not the reverb
        if (auto* p = processor.apvts.getParameter (pid::reverbMix)) p->setValueNotifyingHost (0.0f);
        if (auto* p = processor.apvts.getParameter (pid::delayMix))  p->setValueNotifyingHost (0.0f);
        if (auto* p = processor.apvts.getParameter (pid::chorusAmount)) p->setValueNotifyingHost (0.0f);
        if (auto* p = processor.apvts.getParameter (pid::compAmount)) p->setValueNotifyingHost (0.0f);
        if (auto* p = processor.apvts.getParameter (pid::drive))     p->setValueNotifyingHost (0.0f);

        const int totalSamples = (int) (12.0 * sampleRate);
        AudioBuffer<float> output (2, totalSamples);
        output.clear();

        AudioBuffer<float> block (2, blockSize);
        int written = 0;
        bool sent = false;

        while (written < totalSamples)
        {
            const int numSamples = jmin (blockSize, totalSamples - written);
            block.setSize (2, numSamples, false, false, true);
            block.clear();

            MidiBuffer midi;

            if (! sent)
            {
                midi.addEvent (MidiMessage::controllerEvent (1, 64, 127), 0);
                midi.addEvent (MidiMessage::noteOn (1, midiNote, velocity), 1);
                sent = true;
            }

            processor.processBlock (block, midi);

            for (int ch = 0; ch < 2; ++ch)
                output.copyFrom (ch, written, block, ch, 0, numSamples);

            written += numSamples;
        }

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

    /*  Worst case for the ambience: maximum decay, maximum shimmer in both
        directions, and freeze latched on halfway through. Freeze drives the tank
        to unity gain with a pitch shifter inside the loop, so if anything in
        there can run away, it runs away here.
    */
    bool stressAmbience (String& report)
    {
        WorshipPianoProcessor processor;
        processor.setPlayConfigDetails (0, 2, sampleRate, blockSize);
        processor.prepareToPlay (sampleRate, blockSize);
        processor.loadPreset (13);   // Infinite Wash

        auto set = [&processor] (const char* id, float v)
        {
            if (auto* p = processor.apvts.getParameter (id))
                p->setValueNotifyingHost (p->convertTo0to1 (v));
        };

        set (pid::reverbDecay, 30.0f);
        set (pid::reverbSize, 1.0f);
        set (pid::shimmer, 1.0f);
        set (pid::shimmerMode, 3.0f);
        set (pid::reverbMix, 1.0f);
        set (pid::soak, 1.0f);

        const int totalSamples = (int) (45.0 * sampleRate);
        const int freezeAt = (int) (8.0 * sampleRate);

        AudioBuffer<float> block (2, blockSize);
        int written = 0;
        bool notesSent = false, frozen = false;

        float worstPeak = 0.0f;
        int bad = 0;
        std::vector<float> secondPeaks;
        float peakThisSecond = 0.0f;
        int samplesThisSecond = 0;

        while (written < totalSamples)
        {
            const int numSamples = jmin (blockSize, totalSamples - written);
            block.setSize (2, numSamples, false, false, true);
            block.clear();

            MidiBuffer midi;

            if (! notesSent)
            {
                midi.addEvent (MidiMessage::controllerEvent (1, 64, 127), 0);
                for (int n : { 48, 55, 60, 64, 67, 72 })
                    midi.addEvent (MidiMessage::noteOn (1, n, 0.9f), 1);
                notesSent = true;
            }

            if (! frozen && written >= freezeAt)
            {
                set (pid::reverbFreeze, 1.0f);
                frozen = true;
            }

            processor.processBlock (block, midi);

            for (int ch = 0; ch < 2; ++ch)
                for (int n = 0; n < numSamples; ++n)
                {
                    const float v = block.getSample (ch, n);

                    if (! std::isfinite (v)) { ++bad; continue; }

                    worstPeak = jmax (worstPeak, std::abs (v));
                    peakThisSecond = jmax (peakThisSecond, std::abs (v));
                }

            samplesThisSecond += numSamples;

            if (samplesThisSecond >= (int) sampleRate)
            {
                secondPeaks.push_back (peakThisSecond);
                peakThisSecond = 0.0f;
                samplesThisSecond = 0;
            }

            written += numSamples;
        }

        // after the freeze the tail must hold roughly steady: neither collapse
        // to nothing nor climb away
        float lateMin = 1.0f, lateMax = 0.0f;

        for (size_t i = 20; i < secondPeaks.size(); ++i)
        {
            lateMin = jmin (lateMin, secondPeaks[i]);
            lateMax = jmax (lateMax, secondPeaks[i]);
        }

        report << "ambience stress (max decay + dual shimmer + freeze):" << newLine
               << "   worst peak " << String (Decibels::gainToDecibels (jmax (1.0e-6f, worstPeak)), 1) << " dB"
               << "   frozen tail " << String (Decibels::gainToDecibels (jmax (1.0e-6f, lateMin)), 1)
               << " .. " << String (Decibels::gainToDecibels (jmax (1.0e-6f, lateMax)), 1) << " dB"
               << newLine;

        bool ok = true;

        if (bad > 0)            { report << "   !! " << bad << " non-finite samples" << newLine; ok = false; }
        if (worstPeak > 1.05f)  { report << "   !! output exceeded full scale" << newLine; ok = false; }
        if (lateMin < 1.0e-4f)  { report << "   !! frozen tail collapsed" << newLine; ok = false; }

        report << newLine;
        return ok;
    }

    /** Soak has to do something audible on a preset that starts bone dry. */
    bool checkSoakMacro (String& report)
    {
        report << "soak sweep on Sunday Grand (dry preset):" << newLine;

        std::vector<double> tails;

        for (float soak : { 0.0f, 0.35f, 0.7f, 1.0f })
        {
            WorshipPianoProcessor processor;
            processor.setPlayConfigDetails (0, 2, sampleRate, blockSize);
            processor.prepareToPlay (sampleRate, blockSize);
            processor.loadPreset (0);

            if (auto* p = processor.apvts.getParameter (pid::soak))
                p->setValueNotifyingHost (p->convertTo0to1 (soak));

            const int totalSamples = (int) (10.0 * sampleRate);
            AudioBuffer<float> block (2, blockSize);
            int written = 0;
            bool sent = false;
            double tailSum = 0.0;
            int tailCount = 0;

            while (written < totalSamples)
            {
                const int numSamples = jmin (blockSize, totalSamples - written);
                block.setSize (2, numSamples, false, false, true);
                block.clear();

                MidiBuffer midi;

                if (! sent)
                {
                    for (int n : { 48, 60, 64, 67 })
                        midi.addEvent (MidiMessage::noteOn (1, n, 0.7f), 1);
                    sent = true;
                }

                // everything released after two seconds: what is left is the wash
                if (written < (int) (2.0 * sampleRate) && written + numSamples >= (int) (2.0 * sampleRate))
                    for (int n : { 48, 60, 64, 67 })
                        midi.addEvent (MidiMessage::noteOff (1, n), numSamples - 1);

                processor.processBlock (block, midi);

                if (written > (int) (6.0 * sampleRate))
                    for (int ch = 0; ch < 2; ++ch)
                        for (int n = 0; n < numSamples; ++n)
                        {
                            tailSum += std::abs (block.getSample (ch, n));
                            ++tailCount;
                        }

                written += numSamples;
            }

            const double tail = tailSum / jmax (1, tailCount);
            tails.push_back (tail);

            report << "   soak " << String (roundToInt (soak * 100.0f)).paddedLeft (' ', 4) << " %"
                   << "   wash after release " << String (Decibels::gainToDecibels (jmax (1.0e-7, tail)), 1)
                   << " dB" << newLine;
        }

        const bool rising = tails.back() > tails.front() * 8.0;

        if (! rising)
            report << "   !! soak barely changes anything" << newLine;

        report << newLine;
        return rising;
    }

    /*  Builds an SFZ on disk laid out the way a real piano library is - a
        <control> default_path, a <global> envelope, velocity <group>s, backslash
        separators, and a release-triggered damper group - then loads it back and
        checks the parser and the mapping.
    */
    bool checkSampleLoading (String& report)
    {
        auto dir = File::getSpecialLocation (File::tempDirectory).getChildFile ("wp_sfz_test");
        dir.deleteRecursively();
        auto audioDir = dir.getChildFile ("48khz24bit");
        audioDir.createDirectory();

        WavAudioFormat wav;
        const int roots[3] = { 48, 60, 72 };

        auto writeTone = [&] (const File& file, double freq, float level, double seconds)
        {
            const int length = (int) (sampleRate * seconds);
            AudioBuffer<float> buffer (2, length);

            for (int n = 0; n < length; ++n)
            {
                const float env = std::exp (-3.0f * (float) n / (float) length);
                const float v = std::sin (MathConstants<float>::twoPi * (float) (freq * n / sampleRate))
                              * env * level;
                buffer.setSample (0, n, v);
                buffer.setSample (1, n, v);
            }

            file.deleteFile();
            std::unique_ptr<FileOutputStream> stream (file.createOutputStream());

            if (stream != nullptr)
            {
                std::unique_ptr<AudioFormatWriter> writer (
                    wav.createWriterFor (stream.get(), sampleRate, 2, 24, {}, 0));

                if (writer != nullptr)
                {
                    stream.release();
                    writer->writeFromAudioSampleBuffer (buffer, 0, length);
                }
            }
        };

        for (int r = 0; r < 3; ++r)
        {
            const double freq = 440.0 * std::pow (2.0, (roots[r] - 69) / 12.0);

            for (int layer = 0; layer < 2; ++layer)
                writeTone (audioDir.getChildFile ("note" + String (roots[r]) + "_v" + String (layer) + ".wav"),
                           freq, layer == 0 ? 0.3f : 0.9f, 1.0);

            // damper noise: a short, much quieter burst an octave up
            writeTone (audioDir.getChildFile ("rel" + String (roots[r]) + ".wav"), freq * 2.0, 0.15f, 0.25);
        }

        String sfz;
        sfz << "// a test library" << newLine
            << "<control>" << newLine
            << "default_path=48khz24bit/" << newLine
            << "<global>" << newLine
            << "ampeg_release=0.75 loop_mode=one_shot" << newLine;

        for (int layer = 0; layer < 2; ++layer)
        {
            sfz << "<group> lovel=" << (layer == 0 ? 1 : 64)
                << " hivel=" << (layer == 0 ? 63 : 127)
                << " volume=" << (layer == 0 ? 6 : 0) << newLine;

            for (int r = 0; r < 3; ++r)
                sfz << "<region> sample=48khz24bit\\note" << roots[r] << "_v" << layer
                    << ".wav lokey=" << (roots[r] - 6) << " hikey=" << (roots[r] + 5)
                    << " pitch_keycenter=" << roots[r] << newLine;
        }

        sfz << "// release samples" << newLine
            << "<group> trigger=release volume=-4 rt_decay=2 ampeg_release=0.3" << newLine;

        for (int r = 0; r < 3; ++r)
            sfz << "<region> sample=48khz24bit\\rel" << roots[r]
                << ".wav lokey=" << (roots[r] - 6) << " hikey=" << (roots[r] + 5)
                << " pitch_keycenter=" << roots[r] << newLine;

        auto sfzFile = dir.getChildFile ("test.sfz");
        sfzFile.replaceWithText (sfz);

        wp::SampleLibrary::Ptr library = new wp::SampleLibrary();
        const auto error = library->loadFrom (sfzFile);

        report << "sample library loader:" << newLine;

        if (error.isNotEmpty())
        {
            report << "   !! " << error << newLine << newLine;
            dir.deleteRecursively();
            return false;
        }

        report << "   " << library->getNumRegions() << " regions + "
               << library->getNumReleaseRegions() << " release, "
               << (library->getMemoryUsage() / 1024) << " kB" << newLine;

        bool ok = true;

        auto check = [&report, &ok] (bool condition, const String& what)
        {
            if (! condition)
            {
                report << "   !! " << what << newLine;
                ok = false;
            }
        };

        check (library->getNumRegions() == 6, "expected 6 playable regions");
        check (library->getNumReleaseRegions() == 3, "expected 3 release regions");

        // a release-triggered region must never answer a note-on
        for (int note = 42; note <= 77; note += 5)
            for (int vel : { 20, 64, 120 })
            {
                const auto* region = library->find (note, vel);
                check (region != nullptr, "no region for note " + String (note) + " vel " + String (vel));

                if (region != nullptr)
                    check (std::abs (region->releaseSeconds - 0.75f) < 0.01f,
                           "ampeg_release from <global> did not reach note " + String (note)
                           + " (got " + String (region->releaseSeconds, 3) + ")");
            }

        // ... but must be reachable through the release lookup
        const auto* rel = library->findRelease (60, 64);
        check (rel != nullptr, "no release sample for note 60");

        if (rel != nullptr)
        {
            check (rel->rtDecay > 1.9f && rel->rtDecay < 2.1f, "rt_decay was not parsed");
            check (std::abs (rel->releaseSeconds - 0.3f) < 0.01f, "group ampeg_release did not override global");
        }

        struct Case { int note, vel, expectRoot; };
        const Case cases[] = { { 48, 30, 48 }, { 48, 100, 48 }, { 60, 20, 60 },
                               { 64, 100, 60 }, { 72, 127, 72 }, { 70, 64, 72 } };

        for (const auto& c : cases)
        {
            const auto* region = library->find (c.note, c.vel);

            if (region == nullptr || region->rootNote != c.expectRoot)
                check (false, "note " + String (c.note) + " vel " + String (c.vel) + " mapped to "
                              + (region != nullptr ? String (region->rootNote) : String ("nothing")));
        }

        // the quiet layer carries volume=6, the loud one volume=0
        const auto* quiet = library->find (60, 30);
        const auto* loud  = library->find (60, 110);

        if (quiet != nullptr && loud != nullptr)
            check (quiet->gain > loud->gain * 1.5f, "per-group volume was not applied");

        // and it has to make sound at the right pitch through the engine
        wp::SamplerEngine engine;
        engine.prepare (sampleRate, blockSize);
        engine.setLibrary (library);

        AudioBuffer<float> out (2, (int) (sampleRate * 0.5));
        out.clear();
        engine.render (out.getWritePointer (0), out.getWritePointer (1), 16);
        engine.noteOn (67, 0.8f);

        int written = 16;
        while (written < out.getNumSamples())
        {
            const int n = jmin (blockSize, out.getNumSamples() - written);
            engine.render (out.getWritePointer (0) + written, out.getWritePointer (1) + written, n);
            written += n;
        }

        const float peak = out.getMagnitude (0, 0, out.getNumSamples());

        if (peak < 0.01f)
        {
            check (false, "sampler produced no audio");
        }
        else
        {
            const int fftOrder = 15;
            const int fftSize = 1 << fftOrder;
            dsp::FFT fft (fftOrder);
            std::vector<float> data ((size_t) fftSize * 2, 0.0f);

            for (int n = 0; n < jmin (fftSize, out.getNumSamples()); ++n)
                data[(size_t) n] = out.getSample (0, n);

            fft.performFrequencyOnlyForwardTransform (data.data());

            int bin = 0;
            for (int i = 1; i < fftSize / 2; ++i)
                if (data[(size_t) i] > data[(size_t) bin]) bin = i;

            const double detected = bin * sampleRate / fftSize;
            const double expected = 440.0 * std::pow (2.0, (67 - 69) / 12.0);
            const double cents = 1200.0 * std::log2 (detected / expected);

            report << "   playback pitch " << String (detected, 1) << " Hz, expected "
                   << String (expected, 1) << " Hz (" << String (cents, 1) << " cents)" << newLine;

            check (std::abs (cents) < 15.0, "sampler is playing out of tune");
        }

        report << newLine;
        dir.deleteRecursively();
        return ok;
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
    const int single = argc > 3 ? String (argv[3]).getIntValue() : -1;

    // "note" mode: dry single notes for spectral analysis
    if (argc > 2 && String (argv[2]) == "note")
    {
        for (int note : { 41, 53, 60, 72, 84 })
            renderSingleNote (single >= 0 ? single : 0, note, 0.7f,
                              outputDir.getChildFile ("note_" + String (note) + ".wav"));

        renderSingleNote (0, 60, 0.25f, outputDir.getChildFile ("note_60_soft.wav"));
        renderSingleNote (0, 60, 1.0f,  outputDir.getChildFile ("note_60_hard.wav"));
        std::cout << "single notes written" << std::endl;
        return 0;
    }

    String report;
    bool allOk = checkStateRoundTrip (report);
    allOk &= stressAmbience (report);
    allOk &= checkSoakMacro (report);
    allOk &= checkSampleLoading (report);

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
