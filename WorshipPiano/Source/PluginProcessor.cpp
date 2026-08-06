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
    for (const auto& id : allParameterIDs())
        apvts.removeParameterListener (id, this);
}

void WorshipPianoProcessor::parameterChanged (const String&, float)
{
    if (! loadingPreset.load())
        presetModified = true;
}

//==============================================================================
void WorshipPianoProcessor::prepareToPlay (double newSampleRate, int samplesPerBlock)
{
    sampleRate = newSampleRate;

    piano.prepare (newSampleRate, samplesPerBlock);
    pad.prepare (newSampleRate, samplesPerBlock);
    effects.prepare (newSampleRate, samplesPerBlock);

    keyboardState.reset();
    outputLevel.store (0.0f);
}

void WorshipPianoProcessor::releaseResources()
{
    piano.panic();
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
    wp::EngineSettings es;
    es.model        = param<int> (pid::model);
    es.tone         = param (pid::tone);
    es.attack       = param (pid::attack);
    es.decayScale   = param (pid::decayTime);
    es.dynamicRange = param (pid::dynamicRange);
    es.spread       = 0.40f;
    piano.setSettings (es);

    wp::PadSettings ps;
    const float padDb = param (pid::padLevel);
    ps.level       = padDb <= -59.5f ? 0.0f : Decibels::decibelsToGain (padDb);
    ps.cutoffHz    = param (pid::padTone);
    ps.attackMs    = param (pid::padAttack);
    ps.releaseMs   = param (pid::padRelease);
    ps.detuneCents = 12.0f;
    pad.setSettings (ps);

    wp::EffectSettings fx;
    fx.eqLow         = param (pid::eqLow);
    fx.eqMid         = 0.0f;
    fx.eqHigh        = param (pid::eqHigh);
    fx.eqAir         = param (pid::eqAir);
    fx.compAmount    = param (pid::compAmount);
    fx.compMix       = 1.0f;
    fx.drive         = param (pid::drive);
    fx.driveTone     = 0.5f;
    fx.chorusAmount  = param (pid::chorusAmount);
    fx.chorusRate    = 0.32f;
    fx.delayMix      = param (pid::delayMix);
    fx.delayFeedback = param (pid::delayFeedback);
    fx.delayTone     = 0.45f;
    fx.delayPingPong = 0.80f;
    fx.reverbMix     = param (pid::reverbMix);
    fx.reverbSize    = param (pid::reverbSize);
    fx.reverbDecay   = param (pid::reverbDecay);
    fx.reverbTone    = 0.50f;
    fx.shimmer       = param (pid::shimmer);
    fx.width         = param (pid::width);
    fx.outputGain    = Decibels::decibelsToGain (param (pid::outputGain));

    // a bigger room naturally puts more distance before the first reflection
    fx.reverbPredelay = 10.0f + 65.0f * fx.reverbSize;

    const float delayTime = param<int> (pid::delaySync) != 0
                              ? delaySamplesForDivision (param<int> (pid::delayDiv))
                              : (float) (0.42 * sampleRate);

    fx.delaySamplesL = delayTime;
    fx.delaySamplesR = delayTime;

    effects.setSettings (fx);
}

//==============================================================================
void WorshipPianoProcessor::handleMidiMessage (const MidiMessage& m)
{
    if (m.isNoteOn())
    {
        piano.noteOn (m.getNoteNumber(), m.getFloatVelocity());
        pad.noteOn (m.getNoteNumber(), m.getFloatVelocity());
    }
    else if (m.isNoteOff())
    {
        piano.noteOff (m.getNoteNumber());
        pad.noteOff (m.getNoteNumber());
    }
    else if (m.isController())
    {
        const int cc = m.getControllerNumber();
        const float value = (float) m.getControllerValue() / 127.0f;

        switch (cc)
        {
            case 64:  piano.sustainPedal (value); pad.sustainPedal (value >= 0.45f); break;
            case 66:  piano.sostenutoPedal (value >= 0.5f); break;
            case 67:  piano.softPedal (value); break;
            case 120: piano.panic(); pad.reset(); break;
            case 123: piano.allNotesOff(); pad.allNotesOff(); break;
            default: break;
        }
    }
    else if (m.isAllNotesOff())
    {
        piano.allNotesOff();
        pad.allNotesOff();
    }
    else if (m.isAllSoundOff())
    {
        piano.panic();
        pad.reset();
    }
}

void WorshipPianoProcessor::renderSegment (AudioBuffer<float>& buffer, int start, int numSamples)
{
    if (numSamples <= 0)
        return;

    auto* l = buffer.getWritePointer (0) + start;
    auto* r = buffer.getNumChannels() > 1 ? buffer.getWritePointer (1) + start : l;

    piano.render (l, r, numSamples);
    pad.render (l, r, numSamples);
}

void WorshipPianoProcessor::processBlock (AudioBuffer<float>& buffer, MidiBuffer& midi)
{
    ScopedNoDenormals noDenormals;

    const int numSamples = buffer.getNumSamples();

    for (int ch = getTotalNumInputChannels(); ch < buffer.getNumChannels(); ++ch)
        buffer.clear (ch, 0, numSamples);

    buffer.clear();

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


    effects.process (buffer);


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
