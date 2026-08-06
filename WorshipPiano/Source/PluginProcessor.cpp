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
    libraryStatus = "Brak biblioteki - silnik modelowany";
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

    piano.prepare (newSampleRate, samplesPerBlock);
    sampler.prepare (newSampleRate, samplesPerBlock);
    pad.prepare (newSampleRate, samplesPerBlock);
    effects.prepare (newSampleRate, samplesPerBlock);

    padBuffer.setSize (2, jmax (16, samplesPerBlock), false, false, true);
    setLatencySamples (effects.getLatencySamples());

    keyboardState.reset();
    outputLevel.store (0.0f);
}

void WorshipPianoProcessor::releaseResources()
{
    piano.panic();
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
    const float soak = param (pid::soak);
    const float soak2 = soak * soak;

    wp::EngineSettings es;
    es.model        = param<int> (pid::model);
    es.tone         = param (pid::tone);
    es.attack       = param (pid::attack);
    es.decayScale   = param (pid::decayTime);
    es.dynamicRange = param (pid::dynamicRange);
    es.spread       = 0.40f;
    piano.setSettings (es);

    sampler.setDynamics (es.dynamicRange);
    sampler.setTone (es.tone);
    sampler.setReleaseScale (es.decayScale);

    wp::PadSettings ps;
    const float padDb = param (pid::padLevel);
    const float padGain = padDb <= -59.5f ? 0.0f : Decibels::decibelsToGain (padDb);

    // even with the pad switched off in the preset, Soak brings one in
    ps.level       = jmax (padGain, soak2 * Decibels::decibelsToGain (-7.0f));
    ps.cutoffHz    = param (pid::padTone) * (1.0f - 0.35f * soak);
    ps.attackMs    = param (pid::padAttack) * (1.0f + 1.6f * soak);
    ps.releaseMs   = param (pid::padRelease) * (1.0f + 1.4f * soak);
    ps.detuneCents = 12.0f + 8.0f * soak;
    pad.setSettings (ps);

    wp::EffectSettings fx;
    fx.eqLow         = param (pid::eqLow);
    fx.eqHigh        = param (pid::eqHigh);
    fx.eqAir         = param (pid::eqAir);
    fx.compAmount    = param (pid::compAmount);
    fx.drive         = param (pid::drive);
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
    amb.duck    = param (pid::reverbDuck);
    amb.freeze  = param<int> (pid::reverbFreeze) != 0;

    effects.setAmbience (amb);
}

//==============================================================================
void WorshipPianoProcessor::handleMidiMessage (const MidiMessage& m)
{
    if (m.isNoteOn())
    {
        if (useSampler())
            sampler.noteOn (m.getNoteNumber(), m.getFloatVelocity());
        else
            piano.noteOn (m.getNoteNumber(), m.getFloatVelocity());

        pad.noteOn (m.getNoteNumber(), m.getFloatVelocity());
    }
    else if (m.isNoteOff())
    {
        sampler.noteOff (m.getNoteNumber());
        piano.noteOff (m.getNoteNumber());
        pad.noteOff (m.getNoteNumber());
    }
    else if (m.isController())
    {
        const int cc = m.getControllerNumber();
        const float value = (float) m.getControllerValue() / 127.0f;

        switch (cc)
        {
            case 64:  piano.sustainPedal (value); sampler.sustainPedal (value);
                      pad.sustainPedal (value >= 0.45f); break;
            case 66:  piano.sostenutoPedal (value >= 0.5f); break;
            case 67:  piano.softPedal (value); sampler.softPedal (value); break;
            case 120: piano.panic(); sampler.panic(); pad.reset(); break;
            case 123: piano.allNotesOff(); sampler.allNotesOff(); pad.allNotesOff(); break;
            default: break;
        }
    }
    else if (m.isAllNotesOff())
    {
        piano.allNotesOff();
        sampler.allNotesOff();
        pad.allNotesOff();
    }
    else if (m.isAllSoundOff())
    {
        piano.panic();
        sampler.panic();
        pad.reset();
    }
}

void WorshipPianoProcessor::renderSegment (AudioBuffer<float>& buffer, int start, int numSamples)
{
    if (numSamples <= 0)
        return;

    auto* l = buffer.getWritePointer (0) + start;
    auto* r = buffer.getNumChannels() > 1 ? buffer.getWritePointer (1) + start : l;

    if (useSampler())
        sampler.render (l, r, numSamples);
    else
        piano.render (l, r, numSamples);

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
