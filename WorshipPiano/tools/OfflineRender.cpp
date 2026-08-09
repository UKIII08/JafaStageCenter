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
#include <algorithm>

#include "../Source/PluginProcessor.h"
#include "../Source/Presets.h"
#include "../Source/Parameters.h"
#include "../Source/dsp/SampleLibrary.h"
#include "../Source/dsp/PadLayer.h"

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

    /*  Letting go of a key has to stop the note. Not "start it fading" - stop it,
        on the same timescale a damper does, or fast playing turns into a smear
        because every note you have finished with is still sounding under the
        next one. The library says how long that takes (ampeg_release); the job
        here is to check the engine actually honours it.

        Measured as a ratio against a run that holds the key, so what comes out is
        the release envelope alone and not the sample's own decay.
    */
    bool checkNoteRelease (const File& sfzFile, String& report)
    {
        report << "note release:" << newLine;

        /*  What the plugin itself adds between a key and a sound. Everything
            else a player feels is the audio interface's buffer, which is the
            host's business - but this part is ours, and it is worth a number
            rather than an assumption.
        */
        {
            WorshipPianoProcessor probe;
            probe.setPlayConfigDetails (0, 2, sampleRate, blockSize);
            probe.prepareToPlay (sampleRate, blockSize);

            const int latency = probe.getLatencySamples();

            report << "   plugin's own latency: " << latency << " samples ("
                   << String (1000.0 * latency / sampleRate, 2) << " ms)" << newLine;
        }

        // what the test library writes in its <global>
        const float ampegRelease = 0.75f;

        const int note = 60;
        const double holdSeconds = 0.4;
        const double tailSeconds = 3.0;
        const int window = 512;

        auto capture = [&] (bool releaseTheKey, float decayScale, std::vector<float>& windows,
                            std::vector<float>* raw = nullptr)
        {
            WorshipPianoProcessor processor;
            processor.setPlayConfigDetails (0, 2, sampleRate, blockSize);
            processor.prepareToPlay (sampleRate, blockSize);

            if (! attachLibrary (processor, sfzFile))
                return false;

            auto set = [&processor] (const char* id, float v)
            {
                if (auto* p = processor.apvts.getParameter (id))
                    p->setValueNotifyingHost (p->convertTo0to1 (v));
            };

            // everything that could put a tail of its own on the output goes,
            // so what is left is the note and nothing else
            for (auto* id : { pid::reverbMix, pid::delayMix, pid::chorusAmount,
                              pid::reverseMix, pid::soak, pid::shimmer, pid::drive,
                              pid::compAmount, pid::eqAir, pid::eqLow, pid::eqHigh })
                set (id, 0.0f);

            set (pid::padLevel, -60.0f);
            set (pid::decayTime, decayScale);
            set (pid::pianoLevel, 0.0f);
            set (pid::outputGain, 0.0f);

            processor.reset();

            AudioBuffer<float> block (2, blockSize);
            const int total = (int) (sampleRate * (holdSeconds + tailSeconds));
            const int releaseAt = (int) (sampleRate * holdSeconds);

            int done = 0;
            bool started = false, released = false;
            float windowPeak = 0.0f;
            int windowFill = 0;

            while (done < total)
            {
                const int n = jmin (blockSize, total - done);
                block.setSize (2, n, false, false, true);
                block.clear();

                MidiBuffer midi;

                if (! started)
                {
                    midi.addEvent (MidiMessage::noteOn (1, note, 0.8f), 0);
                    started = true;
                }

                if (releaseTheKey && ! released && done + n > releaseAt)
                {
                    midi.addEvent (MidiMessage::noteOff (1, note), jmax (0, releaseAt - done));
                    released = true;
                }

                processor.processBlock (block, midi);

                for (int i = 0; i < n; ++i)
                {
                    if (done + i >= releaseAt)
                    {
                        if (raw != nullptr)
                            raw->push_back (0.5f * (block.getSample (0, i) + block.getSample (1, i)));

                        windowPeak = jmax (windowPeak,
                                           std::abs (block.getSample (0, i)),
                                           std::abs (block.getSample (1, i)));

                        if (++windowFill >= window)
                        {
                            windows.push_back (windowPeak);
                            windowPeak = 0.0f;
                            windowFill = 0;
                        }
                    }
                }

                done += n;
            }

            return true;
        };

        std::vector<float> releasedRun, heldRun;

        if (! capture (true, 1.0f, releasedRun) || ! capture (false, 1.0f, heldRun))
        {
            report << "   !! library never reached the audio thread" << newLine << newLine;
            return false;
        }

        const int count = jmin ((int) releasedRun.size(), (int) heldRun.size());
        const double perWindow = window / sampleRate;

        // how long until the released note sits this far under the held one
        auto timeToDrop = [&] (float dropDb)
        {
            for (int i = 0; i < count; ++i)
            {
                if (heldRun[(size_t) i] < 1.0e-6f)
                    continue;

                const float ratio = Decibels::gainToDecibels (releasedRun[(size_t) i]
                                                                / heldRun[(size_t) i]);

                if (ratio <= dropDb)
                    return (float) (i * perWindow);
            }

            return -1.0f;
        };

        const float to20 = timeToDrop (-20.0f);
        const float to40 = timeToDrop (-40.0f);
        const float to60 = timeToDrop (-60.0f);

        auto fmt = [] (float t) { return t < 0.0f ? String ("never") : String (t, 3) + " s"; };

        report << "   library ampeg_release: " << String (ampegRelease, 2) << " s" << newLine
               << "   after note off, -20 dB: " << fmt (to20) << newLine
               << "                   -40 dB: " << fmt (to40) << newLine
               << "                   -60 dB: " << fmt (to60) << newLine;

        /*  The envelope is exponential, so it never mathematically reaches zero -
            what matters is that it is inaudible by the time the library said it
            would be. Half a release time of slack, no more: past that a released
            note is still under the next one.
        */
        /*  Sustain at zero: the note stops with the key and the pedal is the
            only thing that holds anything. A pianist playing quickly needs the
            previous note gone before the next one lands, and needs it to stop
            without a click at the end of a five millisecond fade.
        */
        std::vector<float> zeroRun, zeroHeld, zeroRaw;
        capture (true, 0.0f, zeroRun, &zeroRaw);
        capture (false, 0.0f, zeroHeld);

        float zeroTo60 = -1.0f;

        for (int i = 0; i < jmin ((int) zeroRun.size(), (int) zeroHeld.size()); ++i)
        {
            if (zeroHeld[(size_t) i] < 1.0e-6f)
                continue;

            if (Decibels::gainToDecibels (zeroRun[(size_t) i] / zeroHeld[(size_t) i]) <= -20.0f)
            {
                zeroTo60 = (float) (i * perWindow);
                break;
            }
        }

        /*  Whether the stop is a discontinuity or merely a fast fade.

            Comparing against the held run's slew was misleading: releasing a key
            also starts the damper noise sample, which in this library sits an
            octave up, and a higher note moves further between samples for the
            same level. That is not a click, it is a different note.

            An outlier test has no such problem. A discontinuity is one lone step
            far above the rest; a fast fade over a bright sample raises every
            step in the window together and moves the ratio hardly at all.
        */
        std::vector<float> zeroSteps;

        for (size_t i = 1; i < jmin (zeroRaw.size(), (size_t) (sampleRate * 0.2)); ++i)
            zeroSteps.push_back (std::abs (zeroRaw[i] - zeroRaw[i - 1]));

        std::sort (zeroSteps.begin(), zeroSteps.end());

        const float zeroWorst = zeroSteps.empty() ? 0.0f : zeroSteps.back();
        const float zeroTypical = zeroSteps.empty() ? 0.0f
                                : zeroSteps[(size_t) ((double) zeroSteps.size() * 0.99)];
        const float zeroRatio = zeroTypical > 1.0e-8f ? zeroWorst / zeroTypical : 0.0f;


        report << "   Sustain at 0, -20 dB in: " << fmt (zeroTo60)
               << "   worst step vs typical x" << String (zeroRatio, 1) << newLine;

        /*  Under a tenth of a second to twenty down: the previous note is out
            of the way before the next one lands, which is the whole point. The
            damper noise sample keeps sounding after that, as it should - a real
            one does too - so this deliberately does not wait for silence.
        */
        const bool zeroOk = zeroTo60 >= 0.0f && zeroTo60 < 0.10f && zeroRatio < 3.0f;

        const bool ok = to60 >= 0.0f && to60 <= ampegRelease * 1.5f && zeroOk;

        if (to60 < 0.0f || to60 > ampegRelease * 1.5f)
            report << "   !! a released key is still sounding long after the damper should have stopped it"
                   << newLine;

        if (! zeroOk)
            report << "   !! Sustain at 0 does not stop the note cleanly" << newLine;

        report << newLine;
        return ok;
    }

    /*  Metallic ringing in the reverb tail.

        A feedback tank with fixed delay lengths has fixed resonances. Energy
        collects on them, and on a long decay what is left at the end is not a
        room, it is a handful of pitches ringing on - the sound people mean by
        "metallic" or "boxy". Moving the delay lengths slowly stops energy ever
        settling into one mode, which is what the expensive pedals do and what
        their tails sound smooth because of.

        Measured on the tail alone, seconds after the notes have gone, as two
        numbers: spectral flatness, where a smooth dense tail approaches noise
        and a ringing one does not, and how far the worst peak stands above the
        median, which is the ringing itself.
    */
    bool checkReverbTailSmoothness (const File& sfzFile, String& report)
    {
        report << "reverb tail smoothness:" << newLine;

        const int fftOrder = 15;
        const int fftSize = 1 << fftOrder;

        bool ok = true;

        // the machines that carry the longest tails, where ringing shows
        struct Case { const char* name; int machine; };

        const Case cases[] = {
            { "Hall",    1 },
            { "Plate",   2 },
            { "Cloud",   3 },
            { "Bloom",   4 },
            { "Shimmer", 5 },
        };

        for (const auto& c : cases)
        {
            WorshipPianoProcessor processor;
            processor.setPlayConfigDetails (0, 2, sampleRate, blockSize);
            processor.prepareToPlay (sampleRate, blockSize);

            if (! attachLibrary (processor, sfzFile))
            {
                report << "   !! library never reached the audio thread" << newLine << newLine;
                return false;
            }

            auto set = [&processor] (const char* id, float v)
            {
                if (auto* p = processor.apvts.getParameter (id))
                    p->setValueNotifyingHost (p->convertTo0to1 (v));
            };

            // a long, wide, wet tail and nothing else running into it
            set (pid::reverbMachine, (float) c.machine);
            set (pid::reverbMix, 1.0f);
            set (pid::reverbSize, 0.9f);
            set (pid::reverbDecay, 18.0f);
            set (pid::shimmer, 0.0f);
            set (pid::delayMix, 0.0f);
            set (pid::chorusAmount, 0.0f);
            set (pid::reverseMix, 0.0f);
            set (pid::padLevel, -60.0f);
            set (pid::soak, 0.0f);
            set (pid::reverbDuck, 0.0f);

            AudioBuffer<float> block (2, blockSize);

            // a chord held long enough to actually charge the tank: ten
            // milliseconds of input leaves a tail near the numerical floor,
            // where the measurement is of rounding rather than of reverb
            {
                MidiBuffer midi;
                for (int note : { 48, 55, 60, 64, 67 })
                    midi.addEvent (MidiMessage::noteOn (1, note, 0.9f), 0);

                block.clear();
                processor.processBlock (block, midi);
            }

            for (int i = 0; i < (int) (sampleRate * 1.5 / blockSize); ++i)
            {
                block.clear();
                MidiBuffer empty;
                processor.processBlock (block, empty);
            }

            {
                MidiBuffer midi;
                for (int note : { 48, 55, 60, 64, 67 })
                    midi.addEvent (MidiMessage::noteOff (1, note), 0);

                block.clear();
                processor.processBlock (block, midi);
            }

            // let the notes and the early reflections go
            for (int i = 0; i < (int) (sampleRate * 3.0 / blockSize); ++i)
            {
                block.clear();
                MidiBuffer empty;
                processor.processBlock (block, empty);
            }

            /*  Several frames across the tail, not one. A tank standing still
                gives the same spectrum in every frame; one whose delay lengths
                are moving gives a spectrum that wanders. The average movement
                per bin, in dB, is that difference - and unlike a flatness or a
                peak-to-median figure it needs no absolute calibration, because
                it compares the tail against itself.
            */
            const int frames = 8;
            const int usable = (fftSize / 2);
            std::vector<std::vector<float>> spectra;

            for (int f = 0; f < frames; ++f)
            {
                std::vector<float> frame ((size_t) fftSize * 2, 0.0f);

                for (int done = 0; done < fftSize; done += blockSize)
                {
                    block.clear();
                    MidiBuffer empty;
                    processor.processBlock (block, empty);

                    for (int i = 0; i < blockSize && done + i < fftSize; ++i)
                        frame[(size_t) (done + i)] = 0.5f * (block.getSample (0, i)
                                                           + block.getSample (1, i));
                }

                for (int i = 0; i < fftSize; ++i)
                    frame[(size_t) i] *= 0.5f - 0.5f * std::cos (MathConstants<float>::twoPi * i / (fftSize - 1));

                dsp::FFT transform (fftOrder);
                transform.performFrequencyOnlyForwardTransform (frame.data());
                spectra.push_back (std::move (frame));
            }

            const double binHz = sampleRate / fftSize;
            const int from = (int) (200.0 / binHz);
            const int to = jmin (usable, (int) (6000.0 / binHz));

            /*  Each frame is normalised by its own total before comparing, so
                the tail simply getting quieter does not read as movement.
            */
            std::vector<double> frameSum (spectra.size(), 0.0);

            for (size_t f = 0; f < spectra.size(); ++f)
                for (int bin = from; bin < to; ++bin)
                    frameSum[f] += spectra[f][(size_t) bin];

            double movementSum = 0.0;
            int counted = 0;

            for (int bin = from; bin < to; ++bin)
            {
                double mean = 0.0;
                std::vector<double> levels;

                for (size_t f = 0; f < spectra.size(); ++f)
                {
                    if (frameSum[f] < 1.0e-12)
                        continue;

                    const double norm = spectra[f][(size_t) bin] / frameSum[f];
                    const double db = 20.0 * std::log10 (jmax (1.0e-12, norm));
                    levels.push_back (db);
                    mean += db;
                }

                if (levels.size() < 2)
                    continue;

                mean /= (double) levels.size();
                double variance = 0.0;

                for (double v : levels)
                    variance += (v - mean) * (v - mean);

                movementSum += std::sqrt (variance / (double) levels.size());
                ++counted;
            }

            const float movement = counted > 0 ? (float) (movementSum / counted) : 0.0f;

            report << "   " << String (c.name).paddedRight (' ', 10)
                   << "tail movement " << String (movement, 2) << " dB per bin";

            /*  Lower is smoother, which is the opposite of what it looks like.

                A tank standing still has sharp isolated resonances, and bins
                around a sharp peak swing wildly between frames as the mode
                drifts a fraction; a tank whose lines are moving smears that
                energy and every bin becomes steadier. Measured with modulation
                switched off entirely this sits at about 8.2 dB, and with it on
                at about 6 dB - so the threshold is an upper bound, and it is
                here to catch the modulation being lost rather than to grade the
                reverb against anybody else's.
            */
            if (movement > 7.5f)
            {
                report << "   <-- STANDING STILL";
                ok = false;
            }

            report << newLine;
        }

        if (! ok)
            report << "   !! the tail has stopped moving - modulation is not reaching the tank" << newLine;

        report << newLine;
        return ok;
    }

    /*  Mono compatibility, and how dense the pad actually is.

        Two numbers that decide whether a pad sounds expensive.

        The first is what survives a mono sum. Plenty of rooms this will be
        played in run a mono PA, and a pad built by spreading detuned copies hard
        across the stereo field is exactly the thing that partly cancels when the
        two sides are added. A pad that vanishes when the desk is folded to mono
        is not a wide pad, it is a broken one.

        The second is spectral density: how much of the spectrum around each
        harmonic is filled in rather than left as one bare line. That density is
        the difference between one detuned chorus and the thick moving bed a
        Nord or a JP-8000 makes.
    */
    bool checkPadRichness (String& report)
    {
        report << "pad width and density (C4):" << newLine;

        struct Case { const char* name; int type; };

        const Case cases[] = {
            { "Warm Saw",   0 },
            { "Soft Choir", 1 },
            { "Glass",      2 },
            { "Strings",    3 },
            { "Air Vox",    4 },
        };

        const int note = 60;
        const double fundamental = 440.0 * std::pow (2.0, (note - 69) / 12.0);
        const int fftOrder = 15;
        const int fftSize = 1 << fftOrder;

        bool ok = true;

        for (const auto& c : cases)
        {
            wp::PadLayer pad;
            pad.prepare (sampleRate, blockSize);

            wp::PadSettings s;
            s.level = 1.0f;
            s.attackMs = 5.0f;
            s.cutoffHz = 12000.0f;
            s.detuneCents = 14.0f;
            s.voice = (wp::PadVoice) c.type;
            pad.setSettings (s);

            pad.noteOn (note, 1.0f);

            AudioBuffer<float> warm (2, blockSize);

            for (int i = 0; i < (int) (sampleRate * 0.5 / blockSize); ++i)
            {
                warm.clear();
                pad.render (warm.getWritePointer (0), warm.getWritePointer (1), blockSize);
            }

            std::vector<float> mono ((size_t) fftSize * 2, 0.0f);
            double energyL = 0.0, energyR = 0.0, energyMono = 0.0;

            AudioBuffer<float> block (2, blockSize);

            for (int done = 0; done < fftSize; done += blockSize)
            {
                block.clear();
                pad.render (block.getWritePointer (0), block.getWritePointer (1), blockSize);

                for (int i = 0; i < blockSize && done + i < fftSize; ++i)
                {
                    const float l = block.getSample (0, i);
                    const float r = block.getSample (1, i);
                    const float m = 0.5f * (l + r);

                    energyL += (double) l * l;
                    energyR += (double) r * r;
                    energyMono += (double) m * m;

                    mono[(size_t) (done + i)] = m;
                }
            }

            /*  What a mono desk keeps. Two identical sides sum to the same level
                (0 dB); anything out of phase between them loses.
            */
            const double sideAverage = 0.5 * (energyL + energyR);
            const float monoDb = Decibels::gainToDecibels (
                                     (float) std::sqrt (energyMono / jmax (1.0e-20, sideAverage)));

            for (int i = 0; i < fftSize; ++i)
                mono[(size_t) i] *= 0.5f - 0.5f * std::cos (MathConstants<float>::twoPi * i / (fftSize - 1));

            dsp::FFT transform (fftOrder);
            transform.performFrequencyOnlyForwardTransform (mono.data());

            /*  Density, counted as resolvable partials rather than as energy
                either side of a line.

                An earlier version of this split energy by its distance from the
                harmonic, which turned out to measure the window rather than the
                sound: widening the detune moved the inner oscillators from one
                side of the boundary to the other and the number went down while
                the pad got thicker. Counting peaks has no such boundary. One saw
                puts one partial on each harmonic; seven detuned saws put seven
                near it, and that is what is heard as thick.
            */
            const double binHz = sampleRate / fftSize;

            float strongest = 0.0f;

            for (int bin = (int) (80.0 / binHz); bin < (int) (4000.0 / binHz); ++bin)
                strongest = jmax (strongest, mono[(size_t) bin]);

            const float floorLevel = strongest * Decibels::decibelsToGain (-40.0f);
            int partials = 0;

            for (int bin = (int) (80.0 / binHz) + 1; bin < (int) (4000.0 / binHz) - 1; ++bin)
            {
                const float here = mono[(size_t) bin];

                // a local maximum standing clear of its neighbours: one partial,
                // however many bins the window smears it across
                if (here > floorLevel
                    && here > mono[(size_t) (bin - 1)]
                    && here >= mono[(size_t) (bin + 1)])
                    ++partials;
            }

            const float density = (float) partials;

            report << "   " << String (c.name).paddedRight (' ', 12)
                   << "mono sum " << String (monoDb, 1) << " dB"
                   << "   partials " << String ((int) density);

            // below -3 dB the mono desk is losing real level, not just width
            if (monoDb < -3.0f)
            {
                report << "   <-- COLLAPSES IN MONO";
                ok = false;
            }

            report << newLine;
        }

        if (! ok)
            report << "   !! the pad loses level when the desk is folded to mono" << newLine;

        report << newLine;
        return ok;
    }

    /*  Aliasing in the pad oscillators.

        The measurable difference between a pad that sounds expensive and one
        that sounds cheap. A band-limited saw has all its energy on harmonics of
        the note; anything that folds back off the top of the spectrum lands
        between them, at frequencies unrelated to what is being played, and that
        is what a listener hears as harsh or grainy rather than as bright.

        Measured high, at C6, where a saw's harmonics run out of room fastest.
        Everything sitting on a harmonic of the note is signal; everything
        between harmonics, above the fundamental, is not.
    */
    bool checkPadAliasing (String& report)
    {
        report << "pad oscillator aliasing (C6):" << newLine;

        struct Case { const char* name; int type; };

        const Case cases[] = {
            { "Warm Saw",   0 },
            { "Soft Choir", 1 },
            { "Glass",      2 },
            { "Strings",    3 },
            { "Air Vox",    4 },
        };

        const int note = 84;                        // C6, 1046.5 Hz
        const double fundamental = 440.0 * std::pow (2.0, (note - 69) / 12.0);
        const int fftOrder = 15;
        const int fftSize = 1 << fftOrder;

        bool ok = true;

        for (const auto& c : cases)
        {
            wp::PadLayer pad;
            pad.prepare (sampleRate, blockSize);

            wp::PadSettings s;
            s.level = 1.0f;
            s.attackMs = 5.0f;
            s.releaseMs = 500.0f;
            s.cutoffHz = 18000.0f;                  // filter wide open: this is
            s.detuneCents = 0.0f;                   // about the oscillator alone
            s.voice = (wp::PadVoice) c.type;
            pad.setSettings (s);

            pad.noteOn (note, 1.0f);

            // let the swell finish before measuring
            AudioBuffer<float> warm (2, blockSize);

            for (int i = 0; i < (int) (sampleRate * 0.4 / blockSize); ++i)
            {
                warm.clear();
                pad.render (warm.getWritePointer (0), warm.getWritePointer (1), blockSize);
            }

            std::vector<float> fft ((size_t) fftSize * 2, 0.0f);
            AudioBuffer<float> block (2, blockSize);

            for (int done = 0; done < fftSize; done += blockSize)
            {
                block.clear();
                pad.render (block.getWritePointer (0), block.getWritePointer (1), blockSize);

                for (int i = 0; i < blockSize && done + i < fftSize; ++i)
                    fft[(size_t) (done + i)] = block.getSample (0, i);
            }

            // Hann, so harmonics do not smear across the bins between them
            for (int i = 0; i < fftSize; ++i)
                fft[(size_t) i] *= 0.5f - 0.5f * std::cos (MathConstants<float>::twoPi * i / (fftSize - 1));

            dsp::FFT transform (fftOrder);
            transform.performFrequencyOnlyForwardTransform (fft.data());

            const double binHz = sampleRate / fftSize;
            float harmonicEnergy = 0.0f, aliasEnergy = 0.0f;

            for (int bin = 1; bin < fftSize / 2; ++bin)
            {
                const double hz = bin * binHz;

                if (hz < fundamental * 0.5 || hz > sampleRate * 0.48)
                    continue;

                const double ratio = hz / fundamental;
                const double nearest = std::round (ratio);
                const double distance = std::abs (ratio - nearest);

                const float energy = fft[(size_t) bin] * fft[(size_t) bin];

                // within a fifteenth of the spacing counts as on the harmonic,
                // which is comfortably wider than the window smears one
                if (nearest >= 1.0 && distance < 0.07)
                    harmonicEnergy += energy;
                else
                    aliasEnergy += energy;
            }

            const float db = Decibels::gainToDecibels (
                                 std::sqrt (aliasEnergy / jmax (1.0e-20f, harmonicEnergy)));

            report << "   " << String (c.name).paddedRight (' ', 12)
                   << "aliasing " << String (db, 1) << " dB below the harmonics";

            /*  -40 dB is about where folded-back energy stops being a texture on
                top of the note and starts being audible as its own thing.
            */
            if (db > -40.0f)
            {
                report << "   <-- AUDIBLE";
                ok = false;
            }

            report << newLine;
        }

        if (! ok)
            report << "   !! an oscillator is folding energy back into the audible band" << newLine;

        report << newLine;
        return ok;
    }

    /*  Pad voice stealing.

        The pad follows every note the piano plays, and this instrument is played
        with the sustain pedal down, so voices pile up until every new note has
        to take one. Taking one that is still sounding - repitching it where it
        stands - is heard as a blip: the note jumps to another frequency at full
        volume, mid-phase, dragging its filter state along.

        That artefact is invisible to a waveform test. A pitch jump is perfectly
        continuous sample to sample; nothing steps. So this asks the pad directly
        how many voices it took while they were still audible, which has to be
        none - a voice must be faded out first and the new note started from
        silence behind it.
    */
    bool checkPadVoiceStealing (String& report)
    {
        report << "pad voice stealing:" << newLine;

        wp::PadLayer pad;
        pad.prepare (sampleRate, blockSize);

        wp::PadSettings s;
        s.level = 0.5f;
        s.attackMs = 700.0f;
        s.releaseMs = 2200.0f;
        pad.setSettings (s);

        AudioBuffer<float> block (2, blockSize);

        // pedal down and stays down, then eight five note chords: forty notes
        // through a pad, which is an ordinary verse and chorus
        pad.sustainPedal (true);

        // twelve distinct chords, no note repeated between them, so the pad runs
        // well past its voice count and the stealing path is genuinely used
        const int roots[12] = { 24, 29, 34, 39, 44, 49, 54, 59, 64, 69, 74, 79 };

        for (int chord = 0; chord < 12; ++chord)
        {
            for (int interval : { 0, 1, 2, 3, 4 })
                pad.noteOn (roots[chord] + interval, 0.85f);

            const int blocks = (int) (sampleRate * 1.2 / blockSize);

            for (int i = 0; i < blocks; ++i)
            {
                block.clear();
                pad.render (block.getWritePointer (0), block.getWritePointer (1), blockSize);
            }
        }

        const int stolen = pad.getStolenVoiceCount();
        const int hijacked = pad.getHijackedVoiceCount();

        report << "   60 notes on the pedal, 32 voices" << newLine
               << "   voices taken (faded first): " << stolen << newLine
               << "   repitched while sounding:   " << hijacked << newLine;

        // if nothing was ever taken the test proves nothing, so that fails too
        const bool ok = hijacked == 0 && stolen > 0;

        if (hijacked != 0)
            report << "   !! a sounding pad voice was repitched instead of being faded out"
                   << newLine;
        else if (stolen == 0)
            report << "   !! the pad never ran out of voices, so this proved nothing"
                   << newLine;

        report << newLine;
        return ok;
    }

    /*  Clicks while simply playing.

        Not a knob being moved - just notes, the way a set actually runs: chords
        held on the pedal, new ones landing on top, voices being taken from
        whatever was quietest. Any of that stealing a voice, or a grain in the
        shimmer wrapping, puts a step in the output.

        Found by outlier rather than by threshold. A pad is a slow waveform, so
        the overwhelming majority of its sample-to-sample steps sit in a narrow
        band; a discontinuity is a lone value far above that band. Comparing the
        largest step against the 99.99th percentile finds it without needing to
        know how loud the passage happens to be.
    */
    bool checkClicksWhilePlaying (const File& sfzFile, String& report)
    {
        report << "clicks while playing:" << newLine;

        bool ok = true;

        // the presets that lean hardest on the pad and the ambience
        for (int preset : { 6, 7, 9, 10, 13 })
        {
            WorshipPianoProcessor processor;
            processor.setPlayConfigDetails (0, 2, sampleRate, blockSize);
            processor.prepareToPlay (sampleRate, blockSize);
            processor.loadPreset (preset);

            if (! attachLibrary (processor, sfzFile))
            {
                report << "   !! library never reached the audio thread" << newLine << newLine;
                return false;
            }

            if (auto* p = processor.apvts.getParameter (pid::padLevel))
                p->setValueNotifyingHost (p->convertTo0to1 (-6.0f));

            AudioBuffer<float> block (2, blockSize);
            std::vector<float> captured;

            const int seconds = 14;
            const int totalBlocks = (int) (sampleRate * seconds / blockSize);

            // a progression that keeps taking voices: five note chords every
            // bar and a pedal that never comes up, which is how this is played
            const int chords[4][5] = {
                { 48, 55, 60, 64, 67 },
                { 45, 52, 57, 60, 64 },
                { 43, 50, 55, 59, 62 },
                { 41, 48, 53, 57, 60 },
            };

            const int blocksPerChord = (int) (sampleRate * 1.6 / blockSize);
            int chordIndex = 0;

            for (int i = 0; i < totalBlocks; ++i)
            {
                block.clear();
                MidiBuffer midi;

                if (i % blocksPerChord == 0)
                {
                    if (i == 0)
                        midi.addEvent (MidiMessage::controllerEvent (1, 64, 127), 0);

                    for (int note : chords[chordIndex % 4])
                        midi.addEvent (MidiMessage::noteOn (1, note, 0.85f), 1);

                    ++chordIndex;
                }

                processor.processBlock (block, midi);

                for (int n = 0; n < blockSize; ++n)
                    captured.push_back (0.5f * (block.getSample (0, n) + block.getSample (1, n)));
            }

            std::vector<float> steps;
            steps.reserve (captured.size());

            for (size_t i = 1; i < captured.size(); ++i)
                steps.push_back (std::abs (captured[i] - captured[i - 1]));

            auto sorted = steps;
            std::sort (sorted.begin(), sorted.end());

            const float p9999 = sorted[(size_t) ((double) sorted.size() * 0.9999)];
            const float worst = sorted.back();
            const float ratio = p9999 > 1.0e-8f ? worst / p9999 : 0.0f;

            // where, so a failure can be listened to rather than guessed at
            size_t worstAt = 0;

            for (size_t i = 0; i < steps.size(); ++i)
                if (steps[i] >= worst) { worstAt = i; break; }

            report << "   " << String (presets::factory()[(size_t) preset].name).paddedRight (' ', 22)
                   << "worst step " << String (worst, 5)
                   << "   p99.99 " << String (p9999, 5)
                   << "   x" << String (ratio, 1)
                   << "   at " << String ((double) worstAt / sampleRate, 2) << " s";

            /*  Four times the 99.99th percentile. One sample in ten thousand is
                already the top of the waveform's own movement; four times that
                is not the waveform, it is a jump.
            */
            if (ratio > 4.0f)
            {
                report << "   <-- CLICK";
                ok = false;
            }

            report << newLine;
        }

        if (! ok)
            report << "   !! the output steps while notes are simply being played" << newLine;

        report << newLine;
        return ok;
    }

    /*  Clicks under a sounding note.

        Changing a preset, or a knob, while the pad is holding a chord must not
        put a step in the waveform. Anything the player or the app can move
        during a song is a candidate, and a preset change now happens on its own
        every time the song changes - so a click there fires in front of the
        congregation rather than in a rehearsal.

        Measured as a ratio, not an absolute: the worst sample-to-sample step
        just after the change against the worst step the same passage was
        already making. A pad is a slow waveform, so a genuine discontinuity
        stands out by an order of magnitude; a level ramp or a filter sweep does
        not move the ratio at all.
    */
    bool checkParameterClicks (const File& sfzFile, String& report)
    {
        report << "clicks under a held chord:" << newLine;

        struct Case
        {
            const char* name;
            const char* id;       // nullptr = whole preset change
            float value;
            int   presetIndex;
        };

        const Case cases[] = {
            { "pad type",       pid::padType,       3.0f,    -1 },
            { "pad tone",       pid::padTone,       3200.0f, -1 },
            { "pad swell",      pid::padAttack,     2400.0f, -1 },
            { "reverb machine", pid::reverbMachine, 3.0f,    -1 },
            { "reverb size",    pid::reverbSize,    0.95f,   -1 },
            { "reverb decay",   pid::reverbDecay,   14.0f,   -1 },
            { "shimmer voice",  pid::shimmerMode,   2.0f,    -1 },
            { "reverse time",   pid::reverseTime,   3.0f,    -1 },
            { "delay division", pid::delayDiv,      6.0f,    -1 },
            { "preset change",  nullptr,            0.0f,     7 },
        };

        bool ok = true;

        for (const auto& c : cases)
        {
            WorshipPianoProcessor processor;
            processor.setPlayConfigDetails (0, 2, sampleRate, blockSize);
            processor.prepareToPlay (sampleRate, blockSize);
            processor.loadPreset (10);      // Soaking Grand: pad, reverb, delay all live

            if (! attachLibrary (processor, sfzFile))
            {
                report << "   !! library never reached the audio thread" << newLine << newLine;
                return false;
            }

            auto set = [&processor] (const char* id, float v)
            {
                if (auto* p = processor.apvts.getParameter (id))
                    p->setValueNotifyingHost (p->convertTo0to1 (v));
            };

            // a pad that is unmistakably present, so a step in it is a step we
            // can actually see
            set (pid::padLevel, -6.0f);

            AudioBuffer<float> block (2, blockSize);

            // chord down, sustain pedal, then let it settle into its swell
            {
                MidiBuffer midi;
                for (int note : { 48, 55, 60, 64, 67 })
                    midi.addEvent (MidiMessage::noteOn (1, note, 0.8f), 0);
                midi.addEvent (MidiMessage::controllerEvent (1, 64, 127), 1);

                block.clear();
                processor.processBlock (block, midi);
            }

            auto runFor = [&] (double seconds, std::vector<float>& captured)
            {
                const int total = (int) (sampleRate * seconds);

                for (int done = 0; done < total; done += blockSize)
                {
                    const int n = jmin (blockSize, total - done);
                    block.setSize (2, n, false, false, true);
                    block.clear();
                    MidiBuffer empty;
                    processor.processBlock (block, empty);

                    for (int i = 0; i < n; ++i)
                        captured.push_back (0.5f * (block.getSample (0, i) + block.getSample (1, i)));
                }
            };

            std::vector<float> before, after;
            runFor (1.5, before);

            if (c.id != nullptr)
                set (c.id, c.value);
            else
                processor.loadPreset (c.presetIndex);

            runFor (0.35, after);

            auto worstStep = [] (const std::vector<float>& v, size_t from, size_t to)
            {
                float worst = 0.0f;

                for (size_t i = jmax ((size_t) 1, from); i < jmin (to, v.size()); ++i)
                    worst = jmax (worst, std::abs (v[i] - v[i - 1]));

                return worst;
            };

            // what the passage was already doing, over its last half second
            const size_t tail = (size_t) (sampleRate * 0.5);
            const float settled = worstStep (before, before.size() - jmin (tail, before.size()),
                                             before.size());

            // and what it did in the 30 ms around the change
            const float atChange = worstStep (after, 0, (size_t) (sampleRate * 0.03));

            const float ratio = settled > 1.0e-7f ? atChange / settled : 0.0f;

            report << "   " << String (c.name).paddedRight (' ', 16)
                   << "step " << String (atChange, 5)
                   << "   vs settled " << String (settled, 5)
                   << "   x" << String (ratio, 1);

            /*  Three times the slew the passage was already making. Below that a
                step is indistinguishable from the waveform's own movement; above
                it, something jumped.
            */
            if (ratio > 3.0f)
            {
                report << "   <-- CLICK";
                ok = false;
            }

            report << newLine;
        }

        if (! ok)
            report << "   !! something steps the waveform under a sounding note" << newLine;

        report << newLine;
        return ok;
    }

    /*  The link to Jafa Stage Center. The app leaves the current song on disk;
        the piano has to pick up its tempo and its sound without anybody touching
        the laptop - and crucially, has to ignore the file being rewritten for
        every slide and every blackout, which is most of what the app writes.

        The key is deliberately not followed: the chart the player reads has
        already been transposed, so moving the sound too would put the piano a
        second transposition away from the band.
    */
    bool checkStageLink (String& report)
    {
        report << "stage link:" << newLine;

        auto liveFile = wp::StageLink::sharedDirectory().getChildFile ("live.json");
        const auto backup = liveFile.existsAsFile() ? liveFile.loadFileAsString() : String();

        auto write = [&liveFile] (int id, const String& title, const String& key,
                                  int bpm, const String& preset)
        {
            DynamicObject::Ptr o (new DynamicObject());
            o->setProperty ("song_id", id);
            o->setProperty ("title", title);
            o->setProperty ("key", key);
            o->setProperty ("bpm", bpm);
            o->setProperty ("preset", preset);
            liveFile.replaceWithText (JSON::toString (var (o.get())));
        };

        // a song is already up before the plugin is even opened
        write (1, "Pierwsza", "D", 74, "Prayer Room");

        WorshipPianoProcessor processor;
        processor.setPlayConfigDetails (0, 2, sampleRate, blockSize);
        processor.prepareToPlay (sampleRate, blockSize);

        AudioBuffer<float> block (2, blockSize);

        auto pump = [&]
        {
            for (int i = 0; i < 40; ++i)
            {
                MessageManager::getInstance()->runDispatchLoopUntil (25);
                block.clear();
                MidiBuffer empty;
                processor.processBlock (block, empty);
            }
        };

        block.clear();
        { MidiBuffer empty; processor.processBlock (block, empty); }

        const int wanted = presets::indexForName ("Prayer Room");
        const bool openedOnSong = processor.getPresetIndex() == wanted;
        const bool tempoTaken = std::abs (processor.getHostTempo() - 74.0) < 0.5;

        report << "   opened mid-set, landed on the song's sound: "
               << (openedOnSong ? "OK" : "FAILED") << newLine
               << "   tempo taken from the app (no host transport): "
               << (tempoTaken ? "OK" : String (processor.getHostTempo(), 1) + " BPM, expected 74") << newLine;

        // the next song, with a different sound and tempo
        write (2, "Druga", "A", 132, "Arena Anthem");
        pump();

        const bool followed = processor.getPresetIndex() == presets::indexForName ("Arena Anthem")
                                && std::abs (processor.getHostTempo() - 132.0) < 0.5;

        report << "   followed a song change: " << (followed ? "OK" : "FAILED") << newLine;

        /*  Now the noise: the app rewrites this file on every slide of the same
            song, and on the blackout button. A player who reached over and
            turned something between two verses must not have it undone.
        */
        if (auto* p = processor.apvts.getParameter (pid::reverbMix))
            p->setValueNotifyingHost (p->convertTo0to1 (0.81f));

        const float touched = processor.apvts.getRawParameterValue (pid::reverbMix)->load();

        write (2, "Druga", "A", 132, "Arena Anthem");     // next slide
        pump();
        write (2, "Druga", "", 132, "Arena Anthem");      // blackout: key drops out
        pump();

        const float afterNoise = processor.apvts.getRawParameterValue (pid::reverbMix)->load();
        const bool keptTheKnob = std::abs (afterNoise - touched) < 1.0e-4f;

        report << "   slide and blackout left the knobs alone: "
               << (keptTheKnob ? "OK" : "REVERTED") << newLine;

        // a song with no sound of its own must not reset anything either
        write (3, "Trzecia", "G", 0, "");
        pump();

        const float afterBlank = processor.apvts.getRawParameterValue (pid::reverbMix)->load();
        const bool keptOnBlank = std::abs (afterBlank - touched) < 1.0e-4f;
        const auto shown = processor.getStageSong();

        report << "   song with no preset kept the current sound: "
               << (keptOnBlank ? "OK" : "RESET") << newLine
               << "   song on the display: \"" << shown.title << "\"  " << shown.key << newLine;

        if (backup.isNotEmpty())
            liveFile.replaceWithText (backup);
        else
            liveFile.deleteFile();

        const bool ok = openedOnSong && tempoTaken && followed && keptTheKnob
                     && keptOnBlank && shown.title == "Trzecia";

        if (! ok)
            report << "   !! the stage link is not following the app correctly" << newLine;

        report << newLine;
        return ok;
    }

    /*  A preset that names a library is only usable if going back to one already
        read is instant. Re-reading a gigabyte between two songs is not a feature
        anybody would use twice, so the second load has to come off the pool: no
        loader thread, and sound on the very next block.
    */
    bool checkLibraryCache (const File& sfzFile, String& report)
    {
        report << "library pool:" << newLine;

        WorshipPianoProcessor processor;
        processor.setPlayConfigDetails (0, 2, sampleRate, blockSize);
        processor.prepareToPlay (sampleRate, blockSize);

        if (! attachLibrary (processor, sfzFile))
        {
            report << "   !! library never reached the audio thread" << newLine << newLine;
            return false;
        }

        const auto path = processor.getLibraryPath();

        // away and back again, the way switching preset does it
        processor.clearSampleLibrary();
        processor.loadSampleLibrary (File (path));

        // no dispatch loop and no waiting: if this needs the loader, it fails
        const bool noLoaderRan = ! processor.isLoadingLibrary();

        AudioBuffer<float> block (2, blockSize);
        block.clear();
        MidiBuffer empty;
        processor.processBlock (block, empty);

        const bool liveAgain = processor.isSampleSourceActive();

        report << "   second load without touching disk: "
               << (noLoaderRan ? "OK" : "STARTED A LOADER") << newLine
               << "   sounding on the next block:        "
               << (liveAgain ? "OK" : "FAILED") << newLine
               << "   path preserved:                    "
               << (processor.getLibraryPath() == path ? "OK" : "FAILED") << newLine << newLine;

        return noLoaderRan && liveAgain && processor.getLibraryPath() == path;
    }

    /*  The pedalboard. Two things have to hold for every stomp: switching it off
        actually removes the effect, and the transition does not click. The second
        one is the whole reason the ramps exist - a hard cut on a sounding piano
        is exactly the artefact this instrument spent a release getting rid of.
    */
    bool checkStomps (const File& sfzFile, String& report)
    {
        report << "stomps:" << newLine;

        struct Case { const char* id; const char* name; const char* amount; float amountValue; };

        const Case cases[] = {
            { pid::reverbOn,  "reverb",  pid::reverbMix,    0.75f },
            { pid::delayOn,   "delay",   pid::delayMix,     0.60f },
            { pid::chorusOn,  "chorus",  pid::chorusAmount, 0.80f },
            { pid::reverseOn, "reverse", pid::reverseMix,   0.70f },
            { pid::padOn,     "pad",     pid::padLevel,     -6.0f },
            { pid::tackOn,    "tack",    pid::tackAmount,   0.90f },
        };

        bool ok = true;

        for (const auto& c : cases)
        {
            WorshipPianoProcessor processor;
            processor.setPlayConfigDetails (0, 2, sampleRate, blockSize);
            processor.prepareToPlay (sampleRate, blockSize);
            processor.loadPreset (0);
            attachLibrary (processor, sfzFile);

            auto set = [&processor] (const char* id, float v)
            {
                if (auto* p = processor.apvts.getParameter (id))
                    p->setValueNotifyingHost (p->convertTo0to1 (v));
            };

            // strip the preset back to the one effect under test
            for (auto* id : { pid::reverbMix, pid::delayMix, pid::chorusAmount,
                              pid::reverseMix, pid::soak, pid::drive })
                set (id, 0.0f);

            set (pid::padLevel, -60.0f);
            set (pid::tackAmount, 0.0f);

            // the shortest reverse window, or the swell has not come back yet
            // inside the length of this test
            set (pid::reverseTime, 0.0f);
            set (c.amount, c.amountValue);

            auto capture = [&] (bool on, AudioBuffer<float>& out)
            {
                set (c.id, on ? 1.0f : 0.0f);
                processor.reset();

                const int length = (int) (sampleRate * 4.0);
                out.setSize (2, length, false, false, true);
                out.clear();

                int done = 0;
                bool sent = false;

                while (done < length)
                {
                    const int n = jmin (blockSize, length - done);
                    AudioBuffer<float> block (2, n);
                    block.clear();

                    MidiBuffer midi;

                    if (! sent)
                    {
                        for (int note : { 52, 59, 64, 67 })
                            midi.addEvent (MidiMessage::noteOn (1, note, 0.85f), 1);

                        sent = true;
                    }

                    processor.processBlock (block, midi);

                    for (int ch = 0; ch < 2; ++ch)
                        out.copyFrom (ch, done, block, ch, 0, n);

                    done += n;
                }
            };

            AudioBuffer<float> withEffect, without;
            capture (true, withEffect);
            capture (false, without);

            /*  How much the stomp actually does, measured as the energy of the
                difference between the two renders relative to the signal itself.
                Comparing levels instead would only work for effects that add a
                tail - a chorus changes the sound without changing its level, and
                tack only touches the attack.
            */
            double diffEnergy = 0.0, signalEnergy = 0.0;
            const int n = withEffect.getNumSamples();

            for (int ch = 0; ch < 2; ++ch)
            {
                const auto* a = withEffect.getReadPointer (ch);
                const auto* b = without.getReadPointer (ch);

                for (int i = 0; i < n; ++i)
                {
                    const double d = (double) a[i] - (double) b[i];
                    diffEnergy += d * d;
                    signalEnergy += (double) a[i] * a[i];
                }
            }

            const float deltaDb = (float) (10.0 * std::log10 (jmax (1.0e-14, diffEnergy)
                                                            / jmax (1.0e-14, signalEnergy)));

            /*  Now the click test: engage the stomp midway through a sustained
                chord and look for a step between neighbouring samples. A ramp
                cannot produce one; a hard cut does nothing else.
            */
            set (c.id, 1.0f);
            processor.reset();

            const int length = (int) (sampleRate * 3.0);
            AudioBuffer<float> switched (2, length);
            switched.clear();

            int done = 0;
            bool sent = false;
            const int switchAt = (int) (sampleRate * 1.5);

            while (done < length)
            {
                const int n = jmin (blockSize, length - done);
                AudioBuffer<float> block (2, n);
                block.clear();

                MidiBuffer midi;

                if (! sent)
                {
                    for (int note : { 52, 59, 64, 67 })
                        midi.addEvent (MidiMessage::noteOn (1, note, 0.85f), 1);

                    sent = true;
                }

                if (done <= switchAt && done + n > switchAt)
                    set (c.id, 0.0f);

                processor.processBlock (block, midi);

                for (int ch = 0; ch < 2; ++ch)
                    switched.copyFrom (ch, done, block, ch, 0, n);

                done += n;
            }

            float worstStep = 0.0f;
            const int from = jmax (1, switchAt - 2000);
            const int to = jmin (length, switchAt + (int) (sampleRate * 0.5));

            for (int ch = 0; ch < 2; ++ch)
            {
                const auto* d = switched.getReadPointer (ch);

                for (int n = from; n < to; ++n)
                    worstStep = jmax (worstStep, std::abs (d[n] - d[n - 1]));
            }

            report << "   " << String (c.name).paddedRight (' ', 9)
                   << " changes " << String (deltaDb, 1).paddedLeft (' ', 6)
                   << " dB of the signal   worst step at the switch "
                   << String (worstStep, 4) << newLine;

            // -26 dB is about five per cent of the energy: below that a player
            // would not be sure the switch did anything
            if (deltaDb < -26.0f)
            {
                report << "     !! switching this stomp barely changes anything" << newLine;
                ok = false;
            }

            // a click is a step far larger than the waveform's own slew; 0.12
            // sits well above normal sample-to-sample movement at these levels
            if (worstStep > 0.12f)
            {
                report << "     !! that is a click, not a fade" << newLine;
                ok = false;
            }
        }

        report << newLine;
        return ok;
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

        /*  A preset can also carry the sample library it was built on, so a set
            can run a felt piano under one song and a grand under the next. The
            path has to come back exactly - and a preset saved without one has to
            stay without one, or changing preset would drag a library along
            uninvited and stop the stage for a load nobody asked for.
        */
        const String libraryPresetName = "__wp_test_preset_lib";
        presets::deleteUser (libraryPresetName);

        const auto libraryPath = File::getSpecialLocation (File::tempDirectory)
                                     .getChildFile ("some piano.sfz").getFullPathName();

        presets::saveUser (processor.apvts, libraryPresetName, libraryPath);

        String carried = "not empty";
        const bool carriedOK = presets::applyUser (restored.apvts, libraryPresetName, &carried)
                                 && carried == libraryPath;

        // the preset saved further up went to disk without a library
        String none = "not empty";
        const bool noneOK = presets::applyUser (restored.apvts, name, &none) && none.isEmpty();

        presets::deleteUser (libraryPresetName);

        const bool deleted = presets::deleteUser (name);
        const bool gone = ! presets::userPresetNames().contains (name);

        report << "   round trip through disk: "
               << (mismatches == 0 ? "OK" : String (mismatches) + " MISMATCHES") << newLine
               << "   library in preset: " << (carriedOK ? "carried" : "LOST")
               << ", without: " << (noneOK ? "stays empty" : "LEAKED") << newLine
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
        return mismatches == 0 && deleted && gone && safeName && carriedOK && noneOK;
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
                // long enough that a released note can be watched all the way
                // down before the sample itself runs out
                writeTone (audioDir.getChildFile ("note" + String (roots[r]) + "_v" + String (layer) + ".wav"),
                           freq, layer == 0 ? 0.3f : 0.9f, 3.0);

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
    allOk &= checkStomps (sfz, report);
    allOk &= checkLibraryCache (sfz, report);
    allOk &= checkNoteRelease (sfz, report);
    allOk &= checkStageLink (report);
    allOk &= checkParameterClicks (sfz, report);
    allOk &= checkClicksWhilePlaying (sfz, report);
    allOk &= checkPadVoiceStealing (report);
    allOk &= checkPadAliasing (report);
    allOk &= checkPadRichness (report);
    allOk &= checkReverbTailSmoothness (sfz, report);

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
