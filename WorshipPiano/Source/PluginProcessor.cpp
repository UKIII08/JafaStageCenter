#include "PluginProcessor.h"
#include "PluginEditor.h"
#include "Presets.h"

using namespace juce;

WorshipPianoProcessor::WorshipPianoProcessor()
    : AudioProcessor (BusesProperties().withOutput ("Output", AudioChannelSet::stereo(), true)),
      apvts (*this, nullptr, "state", createParameterLayout())
{
    for (const auto& id : allParameterIDs())
        apvts.addParameterListener (id, this);

    presets::apply (apvts, 0);
    currentPreset = 0;
    presetModified = false;
}

WorshipPianoProcessor::~WorshipPianoProcessor()
{
    if (loader != nullptr)
    {
        loader->abort = true;
        loader->stopThread (4000);
    }

    for (const auto& id : allParameterIDs())
        apvts.removeParameterListener (id, this);
}

void WorshipPianoProcessor::parameterChanged (const String&, float)
{
    if (! loadingPreset.load())
        presetModified = true;
}

//==============================================================================
void WorshipPianoProcessor::LibraryLoader::run()
{
    wp::SampleLibrary::Ptr library = new wp::SampleLibrary();

    const auto error = library->loadFrom (source,
                                          [this] (float p) { owner.loadProgress.store (p); },
                                          &abort);

    if (abort.load())
        return;

    // hand the finished library over on the message thread
    MessageManager::callAsync ([safe = WeakReference<WorshipPianoProcessor> (&owner),
                                library, error]
    {
        if (safe != nullptr)
            safe->libraryLoaded (library, error);
    });
}

void WorshipPianoProcessor::libraryLoaded (wp::SampleLibrary::Ptr library, const String& error)
{
    loadProgress.store (1.0f);

    if (error.isNotEmpty() || library == nullptr || library->isEmpty())
    {
        const ScopedLock sl (statusLock);
        libraryStatus = error.isNotEmpty() ? error : "Nie udalo sie zaladowac biblioteki.";
        return;
    }

    // hold on to it here so the audio thread's release never frees anything
    retainedLibraries.add (library);
    sampler.setLibrary (library);
    libraryPath = library->getSourcePath();

    // drop anything nothing else references any more
    for (int i = retainedLibraries.size(); --i >= 0;)
        if (retainedLibraries[i] != library && retainedLibraries[i]->getReferenceCount() == 1)
            retainedLibraries.remove (i);

    {
        const ScopedLock sl (statusLock);
        libraryStatus = library->getName() + "  -  " + String (library->getNumRegions()) + " sampli, "
                      + String (library->getMemoryUsage() / (1024 * 1024)) + " MB";
    }

    updateHostDisplay();
}

void WorshipPianoProcessor::loadSampleLibrary (const File& fileOrFolder)
{
    if (loader != nullptr)
    {
        loader->abort = true;
        loader->stopThread (3000);
    }

    loadProgress.store (0.0f);

    {
        const ScopedLock sl (statusLock);
        libraryStatus = "Wczytywanie: " + fileOrFolder.getFileName() + "...";
    }

    loader = std::make_unique<LibraryLoader> (*this, fileOrFolder);
    loader->startThread (Thread::Priority::low);
}

void WorshipPianoProcessor::clearSampleLibrary()
{
    if (loader != nullptr)
    {
        loader->abort = true;
        loader->stopThread (3000);
        loader.reset();
    }

    sampler.setLibrary (nullptr);
    libraryPath.clear();

    const ScopedLock sl (statusLock);
    libraryStatus = "Brak biblioteki sampli";
}

String WorshipPianoProcessor::getLibraryStatus() const
{
    const ScopedLock sl (statusLock);
    return libraryStatus;
}

//==============================================================================
void WorshipPianoProcessor::prepareToPlay (double newSampleRate, int samplesPerBlock)
{
    sampleRate = newSampleRate;

    sampler.prepare (newSampleRate, samplesPerBlock);
    pad.prepare (newSampleRate, samplesPerBlock);
    effects.prepare (newSampleRate, samplesPerBlock);

    padBuffer.setSize (2, jmax (16, samplesPerBlock), false, false, true);
    setLatencySamples (effects.getLatencySamples());

    keyboardState.reset();
    outputLevel.store (0.0f);
}

void WorshipPianoProcessor::reset()
{
    sampler.panic();
    pad.reset();
    effects.reset();
    padBuffer.clear();
    outputLevel.store (0.0f);
}

void WorshipPianoProcessor::releaseResources()
{
    sampler.panic();
    pad.reset();
    effects.reset();
}

bool WorshipPianoProcessor::isBusesLayoutSupported (const BusesLayout& layouts) const
{
    const auto out = layouts.getMainOutputChannelSet();
    return out == AudioChannelSet::stereo() || out == AudioChannelSet::mono();
}

//==============================================================================
float WorshipPianoProcessor::delaySamplesForDivision (int division) const
{
    static constexpr float beats[] = { 1.0f, 2.0f / 3.0f, 0.75f, 0.5f, 1.0f / 3.0f, 0.375f, 0.25f };
    const int idx = jlimit (0, (int) (sizeof (beats) / sizeof (float)) - 1, division);
    const double beatSeconds = 60.0 / jlimit (20.0, 300.0, hostTempo);

    return (float) (beats[idx] * beatSeconds * sampleRate);
}

void WorshipPianoProcessor::updateSettings()
{
    // Soak is a macro, not a mode: it lifts whatever the preset already does
    // towards a full ambient wash, so it is useful on every preset and does
    // nothing at all at zero.
    auto stomp = [this] (const char* id) { return param (id) > 0.5f ? 1.0f : 0.0f; };

    // Soak is a macro over the whole ambience, so its stomp gates the macro
    // rather than any single stage.
    const float soakRaw = jmax (param (pid::soak), pedalSoak.load());
    const float soak = soakRaw * stomp (pid::soakOn);
    const float soak2 = soak * soak;

    sampler.setDynamics (param (pid::dynamicRange));
    sampler.setTone (param (pid::tone));
    sampler.setReleaseScale (param (pid::decayTime));

    wp::PadSettings ps;
    const float padDb = param (pid::padLevel);
    const float padGain = padDb <= -59.5f ? 0.0f : Decibels::decibelsToGain (padDb);

    /*  Each pad character wants a different filter corner, detune and swell -
        a string section is not a warm saw with a different waveform, it is
        slower and wider as well.
                          cutoff  detune  attack  release  level
    */
    struct PadShape { float cutoff, detune, attack, release, level; };

    static constexpr PadShape shapes[] = {
        { 1.00f, 1.00f, 1.00f, 1.00f, 1.00f },   // Warm Saw
        { 0.62f, 0.75f, 1.35f, 1.30f, 1.15f },   // Soft Choir
        { 2.10f, 0.55f, 0.55f, 0.85f, 0.80f },   // Glass
        { 0.85f, 1.90f, 1.70f, 1.60f, 1.05f },   // Strings
        { 1.45f, 1.25f, 1.15f, 1.10f, 0.90f },   // Air Vox
    };

    const int padVoice = jlimit (0, (int) (sizeof (shapes) / sizeof (PadShape)) - 1,
                                 param<int> (pid::padType));
    const auto& shape = shapes[padVoice];

    ps.voice = (wp::PadVoice) padVoice;

    // even with the pad switched off in the preset, Soak brings one in
    const float padOn = stomp (pid::padOn);
    ps.level       = jmax (padGain, soak2 * Decibels::decibelsToGain (-7.0f))
                   * shape.level * padOn;
    ps.cutoffHz    = param (pid::padTone) * shape.cutoff * (1.0f - 0.35f * soak);
    ps.attackMs    = param (pid::padAttack) * shape.attack * (1.0f + 1.6f * soak);
    ps.releaseMs   = param (pid::padRelease) * shape.release * (1.0f + 1.4f * soak);
    ps.detuneCents = (12.0f + 8.0f * soak) * shape.detune;
    pad.setSettings (ps);

    wp::EffectSettings fx;
    fx.eqLow         = param (pid::eqLow);
    fx.eqHigh        = param (pid::eqHigh);
    fx.eqAir         = param (pid::eqAir);
    fx.compAmount    = param (pid::compAmount);
    fx.drive         = param (pid::drive);
    fx.tackAmount    = param (pid::tackAmount);

    fx.chorusOn  = stomp (pid::chorusOn);
    fx.delayOn   = stomp (pid::delayOn);
    fx.reverseOn = stomp (pid::reverseOn);
    fx.reverbOn  = stomp (pid::reverbOn);
    fx.driveOn   = stomp (pid::driveOn);
    fx.tackOn    = stomp (pid::tackOn);
    fx.chorusAmount  = jmax (param (pid::chorusAmount), soak * 0.30f);
    fx.chorusRate    = 0.32f;

    const float delayMix = param (pid::delayMix);
    fx.delayMix      = delayMix + (1.0f - delayMix) * soak * 0.30f;
    fx.delayFeedback = param (pid::delayFeedback);
    fx.delayTone     = 0.45f;
    fx.delayPingPong = 0.80f;

    const float reverbMix = param (pid::reverbMix);
    fx.reverbMix     = reverbMix + (1.0f - reverbMix) * soak * 0.72f;
    fx.padSend       = 0.85f + 0.85f * soak;
    fx.width         = param (pid::width);
    fx.outputGain    = Decibels::decibelsToGain (param (pid::outputGain));

    const float delayTime = param<int> (pid::delaySync) != 0
                              ? delaySamplesForDivision (param<int> (pid::delayDiv))
                              : (float) (0.42 * sampleRate);

    fx.delaySamplesL = delayTime;
    fx.delaySamplesR = delayTime;

    const float reverseMix = param (pid::reverseMix);
    fx.reverseMix = reverseMix + (1.0f - reverseMix) * soak2 * 0.28f;

    static constexpr float reverseBars[] = { 0.5f, 1.0f, 2.0f, 4.0f };
    const int revIndex = jlimit (0, 3, param<int> (pid::reverseTime));
    const double beatSeconds = 60.0 / jlimit (20.0, 300.0, hostTempo);
    fx.reverseWindow = (float) (reverseBars[revIndex] * 4.0 * beatSeconds * sampleRate);

    effects.setSettings (fx);

    wp::AmbienceSettings amb;
    const int machine = param<int> (pid::reverbMachine);

    // past halfway Soak pushes the reverb into its bigger, slower machines
    amb.machine = soak > 0.55f && machine < 3 ? (soak > 0.8f ? 3 : 4) : machine;

    const float size = param (pid::reverbSize);
    amb.size    = size + (1.0f - size) * soak * 0.65f;
    amb.decay   = param (pid::reverbDecay) * (1.0f + 3.2f * soak2);

    const float shimmer = param (pid::shimmer);
    amb.shimmer = shimmer + (1.0f - shimmer) * soak2 * 0.60f;
    amb.shimmerMode = param<int> (pid::shimmerMode);
    amb.lowCutHz = param (pid::reverbLowCut);
    amb.duck    = param (pid::reverbDuck);
    amb.freeze  = param<int> (pid::reverbFreeze) != 0;

    effects.setAmbience (amb);
}

//==============================================================================
void WorshipPianoProcessor::handleMidiMessage (const MidiMessage& m)
{
    if (m.isNoteOn())
    {
        const int played = m.getNoteNumber();
        const int shift = param<int> (pid::transpose);
        const int sounded = jlimit (0, 127, played + shift);

        // the split is decided by where the finger actually is, not by where
        // the transpose has moved the note to
        const bool padOnly = param<int> (pid::splitOn) != 0
                          && played < param<int> (pid::splitPoint);

        noteTranspose[(size_t) played] = (int8_t) (sounded - played);
        notePadOnly[(size_t) played] = padOnly;

        if (! padOnly)
            sampler.noteOn (sounded, m.getFloatVelocity());

        pad.noteOn (sounded, m.getFloatVelocity());
    }
    else if (m.isNoteOff())
    {
        const int played = m.getNoteNumber();
        const int sounded = jlimit (0, 127, played + (int) noteTranspose[(size_t) played]);

        sampler.noteOff (sounded);
        pad.noteOff (sounded);
    }
    else if (m.isController())
    {
        const int cc = m.getControllerNumber();
        const float value = (float) m.getControllerValue() / 127.0f;

        // expression pedal drives the ambient layer, so the space can be opened
        // and closed with a foot while both hands are busy
        const int pedalMode = param<int> (pid::pedalTarget);

        if ((pedalMode == 1 && cc == 11) || (pedalMode == 2 && cc == 1))
            pedalSoak.store (value);

        /*  The pedalboard, reachable from a foot controller. CC 80-87 are
            "general purpose" in the MIDI spec and every foot controller worth
            owning can send them, so the stomps sit there rather than on
            something a keyboard might already be using.

            Momentary or latching both work: anything past halfway is on.
        */
        static const std::pair<int, const char*> stompCCs[] = {
            { 80, pid::padOn },     { 81, pid::chorusOn }, { 82, pid::delayOn },
            { 83, pid::reverseOn }, { 84, pid::reverbOn }, { 85, pid::soakOn },
            { 86, pid::driveOn },   { 87, pid::tackOn },
        };

        for (const auto& mapping : stompCCs)
        {
            if (cc != mapping.first)
                continue;

            if (auto* p = apvts.getParameter (mapping.second))
            {
                const float wanted = value >= 0.5f ? 1.0f : 0.0f;

                // only write on a real change: setValueNotifyingHost from the
                // audio thread is not free, and a continuous controller sweeping
                // past the midpoint would otherwise spam the host
                if (p->getValue() != wanted)
                    p->setValueNotifyingHost (wanted);
            }
        }

        switch (cc)
        {
            case 64:  sampler.sustainPedal (value);
                      pad.sustainPedal (value >= 0.45f); break;
            case 67:  sampler.softPedal (value); break;
            case 120: panic(); break;
            case 123: sampler.allNotesOff(); pad.allNotesOff(); break;
            default: break;
        }
    }
    else if (m.isAllNotesOff())
    {
        sampler.allNotesOff();
        pad.allNotesOff();
    }
    else if (m.isAllSoundOff())
    {
        panic();
    }
}

void WorshipPianoProcessor::panic()
{
    // Handled at the end of the next block so it can be faded. Cutting the
    // engines and resetting the filters mid-tail is itself a loud click, which
    // is the last thing a panic button should produce on a live desk.
    panicRequested.store (true);
}

void WorshipPianoProcessor::renderSegment (AudioBuffer<float>& buffer, int start, int numSamples)
{
    if (numSamples <= 0)
        return;

    auto* l = buffer.getWritePointer (0) + start;
    auto* r = buffer.getNumChannels() > 1 ? buffer.getWritePointer (1) + start : l;

    sampler.render (l, r, numSamples);

    pad.render (padBuffer.getWritePointer (0) + start,
                padBuffer.getWritePointer (1) + start, numSamples);
}

void WorshipPianoProcessor::processBlock (AudioBuffer<float>& buffer, MidiBuffer& midi)
{
    ScopedNoDenormals noDenormals;

    const int numSamples = buffer.getNumSamples();

    for (int ch = getTotalNumInputChannels(); ch < buffer.getNumChannels(); ++ch)
        buffer.clear (ch, 0, numSamples);

    buffer.clear();

    if (padBuffer.getNumSamples() < numSamples)
        padBuffer.setSize (2, numSamples, false, false, true);

    padBuffer.clear (0, numSamples);

    if (auto* transport = getPlayHead())
        if (const auto position = transport->getPosition())
            if (const auto bpm = position->getBpm())
                hostTempo = *bpm;

    // has to happen before anything asks whether a library is loaded
    sampler.updateLibrary();

    updateSettings();

    keyboardState.processNextMidiBuffer (midi, 0, numSamples, true);

    const float pianoGain = Decibels::decibelsToGain (param (pid::pianoLevel));

    int position = 0;

    for (const auto metadata : midi)
    {
        const int eventTime = jlimit (0, numSamples, metadata.samplePosition);

        if (eventTime > position)
        {
            renderSegment (buffer, position, eventTime - position);
            position = eventTime;
        }

        handleMidiMessage (metadata.getMessage());
    }

    renderSegment (buffer, position, numSamples - position);

    buffer.applyGain (pianoGain);

    effects.process (buffer, padBuffer);


    if (panicRequested.exchange (false))
    {
        // fade this block out, then clear everything from silence
        for (int ch = 0; ch < buffer.getNumChannels(); ++ch)
            buffer.applyGainRamp (ch, 0, numSamples, 1.0f, 0.0f);

            sampler.panic();
        pad.reset();
        effects.reset();
        noteTranspose.fill (0);
        notePadOnly.fill (false);
        keyboardState.allNotesOff (0);
    }

    float peak = 0.0f;

    for (int ch = 0; ch < buffer.getNumChannels(); ++ch)
        peak = jmax (peak, buffer.getMagnitude (ch, 0, numSamples));

    const float previous = outputLevel.load();
    outputLevel.store (peak > previous ? peak : previous * 0.82f);

    midi.clear();
}

//==============================================================================
int WorshipPianoProcessor::getNumPrograms() { return (int) presets::factory().size(); }
int WorshipPianoProcessor::getCurrentProgram() { return jmax (0, currentPreset); }

void WorshipPianoProcessor::setCurrentProgram (int index) { loadPreset (index); }

const String WorshipPianoProcessor::getProgramName (int index)
{
    const auto& list = presets::factory();
    return isPositiveAndBelow (index, (int) list.size()) ? list[(size_t) index].name : String();
}

void WorshipPianoProcessor::loadPreset (int index)
{
    if (! isPositiveAndBelow (index, (int) presets::factory().size()))
        return;

    loadingPreset.store (true);
    presets::apply (apvts, index);
    loadingPreset.store (false);

    currentPreset = index;
    presetModified = false;

    updateHostDisplay();
}

//==============================================================================
void WorshipPianoProcessor::getStateInformation (MemoryBlock& destData)
{
    auto state = apvts.copyState();
    state.setProperty ("presetIndex", currentPreset, nullptr);
    state.setProperty ("presetModified", presetModified.load(), nullptr);
    state.setProperty ("libraryPath", libraryPath, nullptr);

    if (auto xml = state.createXml())
        copyXmlToBinary (*xml, destData);
}

void WorshipPianoProcessor::setStateInformation (const void* data, int sizeInBytes)
{
    auto xml = getXmlFromBinary (data, sizeInBytes);

    if (xml == nullptr || ! xml->hasTagName (apvts.state.getType()))
        return;

    auto tree = ValueTree::fromXml (*xml);

    loadingPreset.store (true);
    apvts.replaceState (tree);
    loadingPreset.store (false);

    currentPreset = (int) tree.getProperty ("presetIndex", 0);
    presetModified = (bool) tree.getProperty ("presetModified", true);

    const String savedPath = tree.getProperty ("libraryPath", String());

    if (savedPath.isNotEmpty() && savedPath != libraryPath)
    {
        const File saved (savedPath);

        if (saved.exists())
            loadSampleLibrary (saved);
        else
        {
            const ScopedLock sl (statusLock);
            libraryStatus = "Nie znaleziono zapisanej biblioteki: " + saved.getFileName();
        }
    }
}

//==============================================================================
AudioProcessorEditor* WorshipPianoProcessor::createEditor()
{
    return new WorshipPianoEditor (*this);
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new WorshipPianoProcessor();
}
