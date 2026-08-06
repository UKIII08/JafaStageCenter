/*
    Offline harness: loads every factory preset, plays a short chord progression
    through the engine and writes a WAV per preset. Used to check that the DSP
    is stable (no NaNs, no runaway feedback, sensible levels) without needing a
    host or an audio device.

    Build with -DWORSHIPPIANO_BUILD_TOOLS=ON, then run:
        ./build/tools/WorshipPianoRender out_dir [presetIndex]
*/

#include <juce_audio_formats/juce_audio_formats.h>

#include <map>

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

    /*  Every test needs a library now: without one the instrument is silent by
        design. Load it and spin until it has actually reached the audio thread,
        because loading happens on a background thread and the handoff is what
        used to be broken.
    */
    bool attachLibrary (WorshipPianoProcessor& processor, const File& sfzFile)
    {
        processor.loadSampleLibrary (sfzFile);

        AudioBuffer<float> warm (2, blockSize);

        for (int i = 0; i < 500; ++i)
        {
            MessageManager::getInstance()->runDispatchLoopUntil (10);
            warm.clear();
            MidiBuffer empty;
            processor.processBlock (warm, empty);

            if (processor.isSampleSourceActive())
                return true;
        }

        return false;
    }

    /*  A preset the player saved before a service has to come back exactly, on
        the next launch and after a reinstall. Round trip it through disk.
    */
    bool checkUserPresets (String& report)
    {
        report << "user presets:" << newLine;

        const String name = "__wp_test_preset";
        presets::deleteUser (name);

        WorshipPianoProcessor processor;
        processor.setPlayConfigDetails (0, 2, sampleRate, blockSize);
        processor.prepareToPlay (sampleRate, blockSize);
        processor.loadPreset (5);

        auto set = [&processor] (const char* id, float v)
        {
            if (auto* p = processor.apvts.getParameter (id))
                p->setValueNotifyingHost (p->convertTo0to1 (v));
        };

        // move things off the preset values so we are testing the file, not
        // the preset that happened to be loaded
        set (pid::reverbDecay, 7.5f);
        set (pid::soak, 0.66f);
        set (pid::transpose, -4.0f);
        set (pid::eqAir, 3.5f);

        std::map<String, float> before;

        for (const auto& id : allParameterIDs())
            before[id] = processor.apvts.getRawParameterValue (id)->load();

        const auto error = presets::saveUser (processor.apvts, name);

        if (error.isNotEmpty())
        {
            report << "   !! " << error << newLine << newLine;
            return false;
        }

        if (! presets::userPresetNames().contains (name))
        {
            report << "   !! saved preset does not show up in the list" << newLine << newLine;
            presets::deleteUser (name);
            return false;
        }

        // wipe the state, then load it back from disk
        processor.loadPreset (0);

        WorshipPianoProcessor restored;
        restored.setPlayConfigDetails (0, 2, sampleRate, blockSize);
        restored.prepareToPlay (sampleRate, blockSize);

        if (! presets::applyUser (restored.apvts, name))
        {
            report << "   !! could not load the preset back" << newLine << newLine;
            presets::deleteUser (name);
            return false;
        }

        int mismatches = 0;

        for (const auto& id : allParameterIDs())
        {
            const float a = before[id];
            const float b = restored.apvts.getRawParameterValue (id)->load();

            if (std::abs (a - b) > 1.0e-4f * jmax (1.0f, std::abs (a)))
            {
                report << "     mismatch on " << id << ": " << a << " vs " << b << newLine;
                ++mismatches;
            }
        }

        const bool deleted = presets::deleteUser (name);
        const bool gone = ! presets::userPresetNames().contains (name);

        report << "   round trip through disk: "
               << (mismatches == 0 ? "OK" : String (mismatches) + " MISMATCHES") << newLine
               << "   delete: " << (deleted && gone ? "OK" : "FAILED") << newLine;

        // a name with characters no file system will take must not silently
        // write somewhere unexpected
        const auto awkward = presets::sanitiseName ("  ../../Sunday: \"Grand\" ?  ");
        report << "   awkward name -> \"" << awkward << "\"" << newLine;

        const bool safeName = ! awkward.contains ("..") && ! awkward.contains ("/")
                           && ! awkward.contains ("\\") && awkward.isNotEmpty();

        if (! safeName)
            report << "   !! a preset name can escape the preset folder" << newLine;

        report << newLine;
        return mismatches == 0 && deleted && gone && safeName;
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
    bool stressAmbience (const File& sfzFile, String& report)
    {
        WorshipPianoProcessor processor;
        processor.setPlayConfigDetails (0, 2, sampleRate, blockSize);
        processor.prepareToPlay (sampleRate, blockSize);
        processor.loadPreset (13);   // Infinite Wash
        attachLibrary (processor, sfzFile);

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
    bool checkSoakMacro (const File& sfzFile, String& report)
    {
        report << "soak sweep on Sunday Grand (dry preset):" << newLine;

        std::vector<double> tails;

        for (float soak : { 0.0f, 0.35f, 0.7f, 1.0f })
        {
            WorshipPianoProcessor processor;
            processor.setPlayConfigDetails (0, 2, sampleRate, blockSize);
            processor.prepareToPlay (sampleRate, blockSize);
            processor.loadPreset (0);
            attachLibrary (processor, sfzFile);

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

    bool checkSampleSourceEndToEnd (const File& sfzFile, String& report);
    bool checkSourceLevelMatch (const File& sfzFile, String& report);

    /*  What the plugin actually costs, stage by stage. Reported as a real time
        factor: 1.0 means rendering one second of audio takes one second of CPU,
        so anything approaching that on this machine will crackle on a laptop.

        Attribution is by subtraction - measure everything, then measure again
        with one stage silenced - which is crude but honest about where the
        milliseconds go.
    */
    void benchmark (const File& sfzFile, String& report)
    {
        report << "cpu, sustained 10 note chord + pedal, sampled source:" << newLine;

        struct Stage { const char* name; std::vector<std::pair<const char*, float>> off; };

        const std::vector<Stage> stages = {
            { "everything on",  {} },
            { "no reverb",      { { pid::reverbMix, 0.0f } } },
            { "no shimmer",     { { pid::shimmer, 0.0f } } },
            { "no reverse",     { { pid::reverseMix, 0.0f } } },
            { "no delay",       { { pid::delayMix, 0.0f } } },
            { "no pad",         { { pid::padLevel, -60.0f } } },
            { "no drive",       { { pid::drive, 0.0f } } },
            { "no chorus",      { { pid::chorusAmount, 0.0f } } },
        };

        for (const auto& stage : stages)
        {
            WorshipPianoProcessor processor;
            processor.setPlayConfigDetails (0, 2, sampleRate, blockSize);
            processor.prepareToPlay (sampleRate, blockSize);
            processor.loadPreset (11);   // Soaking Cloud: the heaviest one
            processor.loadSampleLibrary (sfzFile);

            {
                AudioBuffer<float> warm (2, blockSize);
                bool ready = false;

                for (int i = 0; i < 500 && ! ready; ++i)
                {
                    MessageManager::getInstance()->runDispatchLoopUntil (10);
                    warm.clear();
                    MidiBuffer empty;
                    processor.processBlock (warm, empty);
                    ready = processor.isSampleSourceActive();
                }
            }

            for (auto& p : stage.off)
                if (auto* param = processor.apvts.getParameter (p.first))
                    param->setValueNotifyingHost (param->convertTo0to1 (p.second));

            AudioBuffer<float> block (2, blockSize);

            // ten notes held down with the sustain pedal, which is what a
            // worship player actually does
            MidiBuffer opening;
            for (int i = 0; i < 10; ++i)
                opening.addEvent (MidiMessage::noteOn (1, 40 + i * 4, 0.85f), i);

            opening.addEvent (MidiMessage::controllerEvent (1, 64, 127), 10);

            block.clear();
            processor.processBlock (block, opening);

            const int seconds = 6;
            const int blocks = (int) (sampleRate * seconds / blockSize);
            const double start = Time::getMillisecondCounterHiRes();

            for (int i = 0; i < blocks; ++i)
            {
                block.clear();
                MidiBuffer midi;

                // keep retriggering so voices never all decay away
                if (i % 40 == 0)
                    for (int n = 0; n < 10; ++n)
                        midi.addEvent (MidiMessage::noteOn (1, 40 + n * 4, 0.85f), n);

                processor.processBlock (block, midi);
            }

            const double elapsed = (Time::getMillisecondCounterHiRes() - start) * 0.001;
            const double factor = elapsed / seconds;

            report << "   " << String (stage.name).paddedRight (' ', 16)
                   << String (factor * 100.0, 2).paddedLeft (' ', 6) << " % of real time"
                   << newLine;
        }

        report << newLine;
    }

    /*  Builds an SFZ on disk laid out the way a real piano library is - a
        <control> default_path, a <global> envelope, velocity <group>s, backslash
        separators, and a release-triggered damper group - then loads it back and
        checks the parser and the mapping.
    */
    File buildTestLibrary()
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
        return sfzFile;
    }

    bool checkSampleLoading (const File& sfzFile, String& report)
    {

        wp::SampleLibrary::Ptr library = new wp::SampleLibrary();
        const auto error = library->loadFrom (sfzFile);

        report << "sample library loader:" << newLine;

        if (error.isNotEmpty())
        {
            report << "   !! " << error << newLine << newLine;
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
        check (! engine.hasLibrary(), "library must not go live before the audio thread picks it up");
        engine.updateLibrary();
        check (engine.hasLibrary(), "library never became active after updateLibrary");
        engine.noteOn (67, 0.8f);

        int written = 0;
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
        ok &= checkSampleSourceEndToEnd (sfzFile, report);
        ok &= checkSourceLevelMatch (sfzFile, report);
        return ok;
    }

    /*  Sample libraries are mastered to wildly different levels, and the chain
        behind them - saturator, compressor, output limiter - only behaves if the
        signal arrives in the range it was voiced for. Calibration at load time is
        what keeps a hot library out of the limiter, and this is the check that it
        actually worked.
    */
    bool checkSourceLevelMatch (const File& sfzFile, String& report)
    {
        report << "level calibration and headroom:" << newLine;

        WorshipPianoProcessor processor;
        processor.setPlayConfigDetails (0, 2, sampleRate, blockSize);
        processor.prepareToPlay (sampleRate, blockSize);
        processor.loadSampleLibrary (sfzFile);

        AudioBuffer<float> block (2, blockSize);
        bool live = false;

        for (int i = 0; i < 500 && ! live; ++i)
        {
            MessageManager::getInstance()->runDispatchLoopUntil (10);
            block.clear();
            MidiBuffer midi;
            processor.processBlock (block, midi);
            live = processor.isSampleSourceActive();
        }

        if (! live)
        {
            report << "   !! library never reached the audio thread" << newLine << newLine;
            return false;
        }

        auto set = [&processor] (const char* id, float v)
        {
            if (auto* p = processor.apvts.getParameter (id))
                p->setValueNotifyingHost (p->convertTo0to1 (v));
        };

        // A chord, because that is where the level difference actually bites,
        // and dry, so what we measure is the source and not the tail.
        const int chord[5] = { 48, 55, 60, 64, 67 };

        auto measure = [&] (bool dry, float& peak, float& clipped)
        {
            for (auto* id : { pid::reverbMix, pid::delayMix, pid::chorusAmount, pid::soak,
                              pid::reverseMix, pid::eqAir, pid::eqLow, pid::eqHigh })
                set (id, 0.0f);

            if (dry)
            {
                set (pid::drive, 0.0f);
                set (pid::compAmount, 0.0f);
            }

            set (pid::padLevel, -60.0f);
            // low enough that neither source reaches the output safety clip, so
            // the comparison measures the sources and not the limiter
            set (pid::pianoLevel, dry ? -24.0f : 0.0f);
            set (pid::outputGain, 0.0f);

            processor.reset();

            const int length = (int) (sampleRate * 1.5);
            AudioBuffer<float> captured (2, length);
            captured.clear();

            int done = 0;
            bool sent = false;

            while (done < length)
            {
                const int n = jmin (blockSize, length - done);
                block.setSize (2, n, false, false, true);
                block.clear();

                MidiBuffer midi;

                if (! sent)
                {
                    for (int note : chord)
                        midi.addEvent (MidiMessage::noteOn (1, note, 0.9f), 1);

                    sent = true;
                }

                processor.processBlock (block, midi);

                for (int ch = 0; ch < 2; ++ch)
                    captured.copyFrom (ch, done, block, ch, 0, n);

                done += n;
            }

            peak = captured.getMagnitude (0, length);

            int over = 0;
            for (int ch = 0; ch < 2; ++ch)
            {
                const auto* d = captured.getReadPointer (ch);
                for (int n = 0; n < length; ++n)
                    if (std::abs (d[n]) > 0.999f)
                        ++over;
            }

            clipped = 100.0f * (float) over / (float) (length * 2);
        };

        auto db = [] (float v) { return String (Decibels::gainToDecibels (jmax (1.0e-6f, v)), 1); };

        float dryPeak = 0.0f, wetPeak = 0.0f, dryClip = 0.0f, wetClip = 0.0f;
        measure (true, dryPeak, dryClip);
        measure (false, wetPeak, wetClip);

        // -24 dB of piano level on top of a calibrated library: this is the
        // number that moves if calibration ever drifts
        const float dryDb = Decibels::gainToDecibels (jmax (1.0e-6f, dryPeak));

        report << "   5 note chord, dry at -24 dB piano: " << db (dryPeak) << " dB" << newLine
               << "   through the chain:                 " << db (wetPeak)
               << " dB (" << String (wetClip, 2) << "% clipped)" << newLine;

        // and now the real world: every factory preset, driven by the sampled
        // source, because that is the combination the player actually hears
        report << "   per preset, sampled source, 5 note chord:" << newLine;

        // The output safety clip starts bending at -3 dBFS. Anything peaking
        // above that is inside the limiter on every attack, which on a piano
        // reads as distortion, not as loudness.
        constexpr float kneeDb = -3.0f;
        bool allBelowKnee = true;

        for (int p = 0; p < (int) presets::factory().size(); ++p)
        {
            processor.loadPreset (p);
            processor.reset();

            const int length = (int) (sampleRate * 1.5);
            AudioBuffer<float> captured (2, length);
            captured.clear();

            int done = 0;
            bool sent = false;

            while (done < length)
            {
                const int n = jmin (blockSize, length - done);
                block.setSize (2, n, false, false, true);
                block.clear();

                MidiBuffer midi;

                if (! sent)
                {
                    for (int note : chord)
                        midi.addEvent (MidiMessage::noteOn (1, note, 0.9f), 1);

                    sent = true;
                }

                processor.processBlock (block, midi);

                for (int ch = 0; ch < 2; ++ch)
                    captured.copyFrom (ch, done, block, ch, 0, n);

                done += n;
            }

            int over = 0;
            for (int ch = 0; ch < 2; ++ch)
            {
                const auto* d = captured.getReadPointer (ch);
                for (int n = 0; n < length; ++n)
                    if (std::abs (d[n]) > 0.99f)
                        ++over;
            }

            const float presetPeak = captured.getMagnitude (0, length);
            const float presetPeakDb = Decibels::gainToDecibels (jmax (1.0e-6f, presetPeak));
            const bool hot = presetPeakDb > kneeDb;
            allBelowKnee &= ! hot;

            report << "     " << String (p).paddedLeft (' ', 2) << "  "
                   << String (presets::factory()[(size_t) p].name).paddedRight (' ', 22)
                   << " peak " << db (presetPeak).paddedLeft (' ', 6)
                   << " dB   limited " << String (100.0 * over / (length * 2), 2) << " %"
                   << (hot ? "   !! inside the limiter" : "")
                   << newLine;
        }

        // a calibrated library lands here; drift either way means the loader
        // stopped measuring the samples properly
        const bool matched = dryDb > -27.0f && dryDb < -21.0f;

        if (! matched)
            report << "   !! calibrated level is " << String (dryDb, 1)
                   << " dB, expected around -24 dB - the library is arriving at"
                   << " the wrong level for the chain behind it" << newLine;

        if (! allBelowKnee)
            report << "   !! presets are peaking above " << String (kneeDb, 1)
                   << " dBFS, so the safety clip runs on every attack" << newLine;

        report << newLine;
        return matched && allBelowKnee;
    }

    /*  End to end, through the processor exactly as a host drives it: load a
        library, select the sampled source, and confirm that what comes out is
        the sample rather than the modelled engine quietly standing in.

        This is the check that was missing. The unit test above used to call
        render() before asking whether a library was loaded - the one thing the
        plugin never does - which hid a deadlock: the source only switched once
        a library was active, and the library only became active inside the
        render that the switch was gating.
    */
    bool checkSampleSourceEndToEnd (const File& sfzFile, String& report)
    {
        report << "sampled source end to end:" << newLine;

        WorshipPianoProcessor processor;
        processor.setPlayConfigDetails (0, 2, sampleRate, blockSize);
        processor.prepareToPlay (sampleRate, blockSize);
        processor.loadSampleLibrary (sfzFile);

        AudioBuffer<float> block (2, blockSize);
        bool live = false;

        for (int i = 0; i < 500 && ! live; ++i)
        {
            MessageManager::getInstance()->runDispatchLoopUntil (10);

            block.clear();
            MidiBuffer midi;
            processor.processBlock (block, midi);

            live = processor.isSampleSourceActive();
        }

        if (! live)
        {
            report << "   !! library loaded but never reached the audio thread" << newLine
                   << "      status: " << processor.getLibraryStatus() << newLine << newLine;
            return false;
        }

        report << "   " << processor.getLibraryStatus() << newLine;

        auto set = [&processor] (const char* id, float v)
        {
            if (auto* p = processor.apvts.getParameter (id))
                p->setValueNotifyingHost (p->convertTo0to1 (v));
        };

        for (auto* id : { pid::reverbMix, pid::delayMix, pid::chorusAmount, pid::drive,
                          pid::compAmount, pid::soak, pid::eqAir, pid::eqLow, pid::eqHigh,
                          pid::reverseMix })
            set (id, 0.0f);

        set (pid::padLevel, -60.0f);
        set (pid::pianoLevel, -12.0f);

        // Render the same note from each source and compare. The test samples are
        // pure sines and the modelled engine is all partials, so the ratio of the
        // fundamental to everything above it tells them apart.
        auto measure = [&] (float& peakOut)
        {
            const int length = (int) (sampleRate * 1.0);
            AudioBuffer<float> captured (2, length);
            captured.clear();

            int done = 0;
            bool noteSent = false;

            while (done < length)
            {
                const int n = jmin (blockSize, length - done);
                block.setSize (2, n, false, false, true);
                block.clear();

                MidiBuffer midi;

                if (! noteSent)
                {
                    midi.addEvent (MidiMessage::noteOn (1, 60, 0.8f), 1);
                    noteSent = true;
                }

                processor.processBlock (block, midi);

                for (int ch = 0; ch < 2; ++ch)
                    captured.copyFrom (ch, done, block, ch, 0, n);

                done += n;
            }

            peakOut = captured.getMagnitude (0, 0, length);

            const int fftOrder = 15;
            const int fftSize = 1 << fftOrder;
            dsp::FFT fft (fftOrder);
            std::vector<float> data ((size_t) fftSize * 2, 0.0f);
            const int offset = (int) (sampleRate * 0.05);

            // a rectangular window smears a sine across every bin, which would
            // make even a pure tone look rich in partials
            for (int i = 0; i < fftSize && i + offset < length; ++i)
            {
                const float w = 0.5f * (1.0f - std::cos (MathConstants<float>::twoPi
                                                         * (float) i / (float) (fftSize - 1)));
                data[(size_t) i] = captured.getSample (0, i + offset) * w;
            }

            fft.performFrequencyOnlyForwardTransform (data.data());

            const double f0 = 440.0 * std::pow (2.0, (60 - 69) / 12.0);
            const int fundamentalBin = roundToInt (f0 * fftSize / sampleRate);
            double fundamental = 0.0, rest = 0.0;

            for (int i = 2; i < fftSize / 2; ++i)
            {
                const double energy = (double) data[(size_t) i] * data[(size_t) i];

                if (std::abs (i - fundamentalBin) <= 4) fundamental += energy;
                else if (i > fundamentalBin + 4)        rest += energy;
            }

            return 10.0 * std::log10 (jmax (1.0e-12, fundamental) / jmax (1.0e-12, rest));
        };

        float peakSampled = 0.0f;
        const double sampledRatio = measure (peakSampled);

        report << "   " << String (sampledRatio, 1) << " dB fundamental vs partials, peak "
               << String (Decibels::gainToDecibels (jmax (1.0e-6f, peakSampled)), 1) << " dB" << newLine;

        bool ok = true;

        if (peakSampled < 0.002f)
        {
            report << "   !! no audio from the sampled source" << newLine;
            ok = false;
        }

        // the test samples are pure sines, so if what comes out is really the
        // sample then almost all the energy sits on the fundamental
        if (sampledRatio < 25.0)
        {
            report << "   !! output does not look like the sample that was loaded" << newLine;
            ok = false;
        }

        report << newLine;
        return ok;
    }

    /** Transpose has to move the pitch, and split has to keep the piano out of
        the left hand. Both rewrite note numbers on their way in, which is easy
        to get subtly wrong and impossible to notice until a rehearsal. */
    bool checkPerformanceControls (const File& sfzFile, String& report)
    {
        report << "performance controls:" << newLine;

        WorshipPianoProcessor processor;
        processor.setPlayConfigDetails (0, 2, sampleRate, blockSize);
        processor.prepareToPlay (sampleRate, blockSize);
        attachLibrary (processor, sfzFile);

        auto set = [&processor] (const char* id, float v)
        {
            if (auto* p = processor.apvts.getParameter (id))
                p->setValueNotifyingHost (p->convertTo0to1 (v));
        };

        // dry, so what is measured is the note and not the room around it
        for (auto* id : { pid::reverbMix, pid::delayMix, pid::chorusAmount, pid::drive,
                          pid::compAmount, pid::soak, pid::reverseMix })
            set (id, 0.0f);

        set (pid::padLevel, -60.0f);

        auto playAndMeasure = [&] (int note, float& peakOut)
        {
            const int length = (int) (sampleRate * 0.7);
            AudioBuffer<float> captured (2, length);
            captured.clear();

            AudioBuffer<float> block (2, blockSize);

            // let the previous note and the panic fade fall away before the
            // window opens, otherwise every measurement carries the last one
            for (int i = 0; i < (int) (sampleRate * 0.6) / blockSize; ++i)
            {
                block.setSize (2, blockSize, false, false, true);
                block.clear();
                MidiBuffer empty;
                processor.processBlock (block, empty);
            }

            int done = 0;
            bool sent = false;

            while (done < length)
            {
                const int n = jmin (blockSize, length - done);
                block.setSize (2, n, false, false, true);
                block.clear();

                MidiBuffer midi;

                if (! sent) { midi.addEvent (MidiMessage::noteOn (1, note, 0.8f), 1); sent = true; }

                processor.processBlock (block, midi);

                for (int ch = 0; ch < 2; ++ch)
                    captured.copyFrom (ch, done, block, ch, 0, n);

                done += n;
            }

            peakOut = captured.getMagnitude (0, 0, length);

            const int fftOrder = 15;
            const int fftSize = 1 << fftOrder;
            dsp::FFT fft (fftOrder);
            std::vector<float> data ((size_t) fftSize * 2, 0.0f);
            const int offset = (int) (sampleRate * 0.05);

            for (int i = 0; i < fftSize && i + offset < length; ++i)
            {
                const float w = 0.5f * (1.0f - std::cos (MathConstants<float>::twoPi
                                                         * (float) i / (float) (fftSize - 1)));
                data[(size_t) i] = captured.getSample (0, i + offset) * w;
            }

            fft.performFrequencyOnlyForwardTransform (data.data());

            int bin = 1;
            for (int i = 2; i < fftSize / 2; ++i)
                if (data[(size_t) i] > data[(size_t) bin]) bin = i;

            processor.panic();
            return bin * sampleRate / fftSize;
        };

        bool ok = true;

        auto check = [&report, &ok] (bool condition, const String& what)
        {
            if (! condition) { report << "   !! " << what << newLine; ok = false; }
        };

        float peak = 0.0f;

        // ---- transpose ------------------------------------------------------
        for (int shift : { 0, 5, -7, 12 })
        {
            set (pid::transpose, (float) shift);

            const double detected = playAndMeasure (60, peak);
            const double expected = 440.0 * std::pow (2.0, (60 + shift - 69) / 12.0);
            const double cents = 1200.0 * std::log2 (jmax (1.0, detected) / expected);

            report << "   transpose " << String (shift).paddedLeft (' ', 3) << ": "
                   << String (detected, 1) << " Hz, expected " << String (expected, 1)
                   << " Hz (" << String (cents, 1) << " cents)" << newLine;

            check (std::abs (cents) < 25.0, "transpose " + String (shift) + " is off pitch");
        }

        set (pid::transpose, 0.0f);

        // ---- split ----------------------------------------------------------
        set (pid::splitPoint, 60.0f);

        // measure the same low note with the split off and on: comparing the two
        // separates a real leak from whatever noise floor the chain always has
        set (pid::splitOn, 0.0f);
        float openPeak = 0.0f, silencePeak = 0.0f;
        playAndMeasure (48, openPeak);

        set (pid::splitOn, 1.0f);
        float belowPeak = 0.0f, abovePeak = 0.0f;
        playAndMeasure (48, belowPeak);
        playAndMeasure (67, abovePeak);

        // and with nothing played at all, for reference
        {
            const int length = (int) (sampleRate * 0.7);
            AudioBuffer<float> quiet (2, length);
            quiet.clear();
            AudioBuffer<float> block (2, blockSize);
            int done = 0;

            while (done < length)
            {
                const int n = jmin (blockSize, length - done);
                block.setSize (2, n, false, false, true);
                block.clear();
                MidiBuffer midi;
                processor.processBlock (block, midi);

                for (int ch = 0; ch < 2; ++ch)
                    quiet.copyFrom (ch, done, block, ch, 0, n);

                done += n;
            }

            silencePeak = quiet.getMagnitude (0, 0, length);
        }

        auto db = [] (float v) { return String (Decibels::gainToDecibels (jmax (1.0e-6f, v)), 1); };

        report << "   low note, split off: " << db (openPeak) << " dB" << newLine
               << "   low note, split on:  " << db (belowPeak) << " dB" << newLine
               << "   above split:         " << db (abovePeak) << " dB" << newLine
               << "   nothing played:      " << db (silencePeak) << " dB" << newLine;

        check (abovePeak > 0.01f, "nothing sounds above the split point");
        check (belowPeak < openPeak * 0.05f, "split does not keep the piano out of the left hand");

        report << newLine;
        return ok;
    }

    bool renderPreset (int presetIndex, const File& sfzFile, const File& outputDir, String& report)
    {
        WorshipPianoProcessor processor;
        processor.setPlayConfigDetails (0, 2, sampleRate, blockSize);
        processor.prepareToPlay (sampleRate, blockSize);
        processor.loadPreset (presetIndex);
        attachLibrary (processor, sfzFile);

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
    const File sfz = buildTestLibrary();

    benchmark (sfz, report);

    bool allOk = checkStateRoundTrip (report);
    allOk &= checkUserPresets (report);
    allOk &= stressAmbience (sfz, report);
    allOk &= checkSoakMacro (sfz, report);
    allOk &= checkSampleLoading (sfz, report);
    allOk &= checkPerformanceControls (sfz, report);

    for (int i = 0; i < (int) presets::factory().size(); ++i)
    {
        if (single >= 0 && i != single)
            continue;

        allOk &= renderPreset (i, sfz, outputDir, report);
    }

    sfz.getParentDirectory().deleteRecursively();

    std::cout << report << std::endl;
    std::cout << (allOk ? "ALL PRESETS OK" : "PROBLEMS FOUND") << std::endl;

    return allOk ? 0 : 1;
}
