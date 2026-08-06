#include "SampleLibrary.h"

#include <regex>

using namespace juce;

namespace wp
{

namespace
{
    constexpr int64 memoryLimitBytes = (int64) 3 * 1024 * 1024 * 1024;

    /** "c#4", "Db2", "A0" or a bare MIDI number. Middle C is 60. */
    int parseNoteName (const String& raw, int fallback = -1)
    {
        auto text = raw.trim().toLowerCase();

        if (text.isEmpty())
            return fallback;

        if (text.containsOnly ("0123456789"))
            return text.getIntValue();

        static const int semitone[7] = { 9, 11, 0, 2, 4, 5, 7 };   // a b c d e f g

        const int letter = text[0] - 'a';

        if (! isPositiveAndBelow (letter, 7))
            return fallback;

        int value = semitone[letter];
        int index = 1;

        while (index < text.length() && (text[index] == '#' || text[index] == 'b' || text[index] == 's'))
        {
            value += (text[index] == 'b') ? -1 : 1;
            ++index;
        }

        const auto octaveText = text.substring (index);

        if (octaveText.isEmpty() || ! octaveText.containsOnly ("-0123456789"))
            return fallback;

        return value + (octaveText.getIntValue() + 1) * 12;
    }

    /** Pulls a root note out of a file name like "Piano_C#3_v4.wav". */
    int rootNoteFromFileName (const String& fileName)
    {
        static const std::regex noteExpr ("(^|[^a-zA-Z])([A-Ga-g])([#sb]?)(-?[0-9])(?![0-9])");

        const auto text = fileName.toStdString();
        std::smatch match;

        if (std::regex_search (text, match, noteExpr))
        {
            const String note = String (match[2].str()) + String (match[3].str()) + String (match[4].str());
            const int value = parseNoteName (note);

            if (isPositiveAndBelow (value, 128))
                return value;
        }

        // otherwise look for a bare MIDI number in the playable range
        static const std::regex numberExpr ("(^|[^0-9])([0-9]{1,3})(?![0-9])");
        auto begin = std::sregex_iterator (text.begin(), text.end(), numberExpr);

        for (auto it = begin; it != std::sregex_iterator(); ++it)
        {
            const int value = String ((*it)[2].str()).getIntValue();

            if (value >= 21 && value <= 108)
                return value;
        }

        return -1;
    }
}

//==============================================================================
bool SampleLibrary::readAudio (const File& file, Region& region, AudioFormatManager& formats)
{
    std::unique_ptr<AudioFormatReader> reader (formats.createReaderFor (file));

    if (reader == nullptr || reader->lengthInSamples <= 0)
        return false;

    const int numChannels = jlimit (1, 2, (int) reader->numChannels);
    const int numSamples = (int) jmin (reader->lengthInSamples, (int64) 60 * 96000);

    region.audio.setSize (numChannels, numSamples);
    reader->read (&region.audio, 0, numSamples, 0, true, numChannels > 1);
    region.sourceRate = reader->sampleRate > 0.0 ? reader->sampleRate : 44100.0;

    memoryBytes += (int64) numChannels * numSamples * (int64) sizeof (float);

    // honour loop points embedded in the file unless the SFZ overrode them
    if (! region.loops && reader->metadataValues.containsKey ("Loop0Start"))
    {
        region.loopStart = reader->metadataValues["Loop0Start"].getIntValue();
        region.loopEnd = reader->metadataValues["Loop0End"].getIntValue();
        region.loops = region.loopEnd > region.loopStart + 16;
    }

    region.loopStart = jlimit (0, numSamples - 1, region.loopStart);
    region.loopEnd = jlimit (region.loopStart + 1, numSamples, region.loopEnd > 0 ? region.loopEnd : numSamples);

    if (region.loopEnd - region.loopStart < 32)
        region.loops = false;

    return true;
}

//==============================================================================
String SampleLibrary::loadFrom (const File& fileOrFolder,
                                std::function<void (float)> onProgress,
                                const std::atomic<bool>* shouldAbort)
{
    regions.clear();
    memoryBytes = 0;
    name = fileOrFolder.getFileNameWithoutExtension();
    sourcePath = fileOrFolder.getFullPathName();

    if (! fileOrFolder.exists())
        return "Nie znaleziono: " + fileOrFolder.getFullPathName();

    const auto error = fileOrFolder.isDirectory() ? loadFolder (fileOrFolder, onProgress, shouldAbort)
                                                  : loadSfz (fileOrFolder, onProgress, shouldAbort);

    if (error.isNotEmpty())
    {
        regions.clear();
        return error;
    }

    if (regions.empty())
        return "Nie znaleziono zadnych sampli w: " + fileOrFolder.getFullPathName();

    buildLookup();
    return {};
}

String SampleLibrary::loadSfz (const File& file, std::function<void (float)>& onProgress,
                               const std::atomic<bool>* shouldAbort)
{
    auto text = file.loadFileAsString();

    if (text.isEmpty())
        return "Pusty plik SFZ.";

    // strip line comments
    {
        StringArray lines;
        lines.addLines (text);

        for (auto& line : lines)
        {
            const int comment = line.indexOf ("//");

            if (comment >= 0)
                line = line.substring (0, comment);
        }

        text = lines.joinIntoString (" ");
    }

    struct Opcodes : std::map<String, String> {};

    Opcodes global, group, current;
    bool inRegion = false;
    File defaultPath = file.getParentDirectory();

    std::vector<Opcodes> pendingRegions;

    const auto raw = text.toStdString();
    static const std::regex tokenExpr ("(<[a-zA-Z_]+>)|([a-zA-Z0-9_]+)=");

    std::vector<std::pair<std::string, std::pair<size_t, size_t>>> tokens;   // key, (valueStart, tokenStart)

    for (auto it = std::sregex_iterator (raw.begin(), raw.end(), tokenExpr);
         it != std::sregex_iterator(); ++it)
    {
        const auto& m = *it;

        if (m[1].matched)
            tokens.push_back ({ m[1].str(), { 0, (size_t) m.position (0) } });
        else
            tokens.push_back ({ m[2].str(), { (size_t) (m.position (0) + m.length (0)), (size_t) m.position (0) } });
    }

    auto finishRegion = [&]
    {
        if (! inRegion)
            return;

        Opcodes merged = global;
        for (const auto& kv : group)   merged[kv.first] = kv.second;
        for (const auto& kv : current) merged[kv.first] = kv.second;
        pendingRegions.push_back (merged);
        current.clear();
        inRegion = false;
    };

    for (size_t i = 0; i < tokens.size(); ++i)
    {
        const auto& key = tokens[i].first;

        if (! key.empty() && key.front() == '<')
        {
            finishRegion();

            if (key == "<global>")      { global.clear(); group.clear(); }
            else if (key == "<master>") { group.clear(); }
            else if (key == "<group>")  { group.clear(); }
            else if (key == "<region>") { inRegion = true; }

            continue;
        }

        const size_t valueStart = tokens[i].second.first;
        const size_t valueEnd = (i + 1 < tokens.size()) ? tokens[i + 1].second.second : raw.size();
        String value = String (raw.substr (valueStart, valueEnd - valueStart)).trim();

        if (key == "default_path")
            defaultPath = file.getParentDirectory().getChildFile (value.replaceCharacter ('\\', '/'));
        else if (inRegion)
            current[String (key)] = value;
        else
            group[String (key)] = value;
    }

    finishRegion();

    if (pendingRegions.empty())
        return "Plik SFZ nie zawiera zadnych <region>.";

    AudioFormatManager formats;
    formats.registerBasicFormats();

    std::map<String, size_t> alreadyLoaded;
    regions.reserve (pendingRegions.size());

    for (size_t i = 0; i < pendingRegions.size(); ++i)
    {
        if (shouldAbort != nullptr && shouldAbort->load())
            return "Ladowanie przerwane.";

        if (onProgress)
            onProgress ((float) i / (float) pendingRegions.size());

        const auto& op = pendingRegions[i];

        auto get = [&op] (const char* k, const String& fallback = {}) -> String
        {
            const auto it = op.find (k);
            return it != op.end() ? it->second : fallback;
        };

        const auto samplePath = get ("sample");

        if (samplePath.isEmpty())
            continue;

        auto sampleFile = defaultPath.getChildFile (samplePath.replaceCharacter ('\\', '/'));

        if (! sampleFile.existsAsFile())
        {
            sampleFile = file.getParentDirectory().getChildFile (samplePath.replaceCharacter ('\\', '/'));

            if (! sampleFile.existsAsFile())
                continue;
        }

        Region region;

        const int key = parseNoteName (get ("key"), -1);
        region.rootNote = parseNoteName (get ("pitch_keycenter"), key >= 0 ? key : 60);
        region.loKey = key >= 0 ? key : parseNoteName (get ("lokey"), 0);
        region.hiKey = key >= 0 ? key : parseNoteName (get ("hikey"), 127);
        region.loVel = get ("lovel", "1").getIntValue();
        region.hiVel = get ("hivel", "127").getIntValue();

        region.gain = Decibels::decibelsToGain (get ("volume", "0").getFloatValue());

        const float cents = get ("tune", get ("pitch", "0")).getFloatValue()
                          + get ("transpose", "0").getFloatValue() * 100.0f;
        region.tuneRatio = std::pow (2.0f, cents / 1200.0f);

        const auto loopMode = get ("loop_mode", get ("loopmode", "no_loop"));
        region.loops = loopMode.containsIgnoreCase ("loop_continuous")
                    || loopMode.containsIgnoreCase ("loop_sustain");
        region.loopStart = get ("loop_start", get ("loopstart", "0")).getIntValue();
        region.loopEnd = get ("loop_end", get ("loopend", "0")).getIntValue();

        region.releaseSeconds = jlimit (0.02f, 12.0f, get ("ampeg_release", "0.4").getFloatValue());
        region.attackSeconds = jlimit (0.0f, 2.0f, get ("ampeg_attack", "0").getFloatValue());

        if (memoryBytes > memoryLimitBytes)
            return "Biblioteka przekracza 3 GB - za duza, zeby zaladowac ja do pamieci.";

        if (! readAudio (sampleFile, region, formats))
            continue;

        regions.push_back (std::move (region));
    }

    return {};
}

String SampleLibrary::loadFolder (const File& folder, std::function<void (float)>& onProgress,
                                  const std::atomic<bool>* shouldAbort)
{
    // a folder might just be a wrapper around an sfz
    {
        auto sfzFiles = folder.findChildFiles (File::findFiles, false, "*.sfz");

        if (! sfzFiles.isEmpty())
        {
            name = sfzFiles[0].getFileNameWithoutExtension();
            sourcePath = sfzFiles[0].getFullPathName();
            return loadSfz (sfzFiles[0], onProgress, shouldAbort);
        }
    }

    auto files = folder.findChildFiles (File::findFiles, true, "*.wav;*.flac;*.aif;*.aiff;*.ogg");
    files.sort();

    if (files.isEmpty())
        return "Folder nie zawiera plikow audio.";

    AudioFormatManager formats;
    formats.registerBasicFormats();

    // group by root note taken from the file name
    std::map<int, Array<File>> byNote;

    for (const auto& f : files)
    {
        const int root = rootNoteFromFileName (f.getFileNameWithoutExtension());

        if (root >= 0)
            byNote[root].add (f);
    }

    if (byNote.empty())
        return "Nie udalo sie odczytac wysokosci dzwieku z nazw plikow.\n"
               "Nazwy powinny zawierac nute (np. Piano_C4.wav) albo numer MIDI 21-108.";

    std::vector<int> roots;
    for (const auto& kv : byNote)
        roots.push_back (kv.first);

    int done = 0;

    for (size_t i = 0; i < roots.size(); ++i)
    {
        if (shouldAbort != nullptr && shouldAbort->load())
            return "Ladowanie przerwane.";

        const int root = roots[i];
        const auto& group = byNote[root];

        // each sample covers the keys up to halfway to its neighbours
        const int previous = i > 0 ? roots[i - 1] : root - 24;
        const int next = i + 1 < roots.size() ? roots[i + 1] : root + 24;
        const int loKey = i > 0 ? (previous + root + 1) / 2 : 0;
        const int hiKey = i + 1 < roots.size() ? (root + next - 1) / 2 : 127;

        // several files on the same note are treated as velocity layers, in
        // file name order (which is how libraries usually number them)
        const int layers = group.size();

        for (int v = 0; v < layers; ++v)
        {
            if (onProgress)
                onProgress ((float) done / (float) files.size());

            Region region;
            region.rootNote = root;
            region.loKey = loKey;
            region.hiKey = hiKey;
            region.loVel = layers == 1 ? 1 : 1 + (127 * v) / layers;
            region.hiVel = layers == 1 ? 127 : (127 * (v + 1)) / layers;
            region.releaseSeconds = 0.4f;

            if (memoryBytes > memoryLimitBytes)
                return "Biblioteka przekracza 3 GB - za duza, zeby zaladowac ja do pamieci.";

            if (readAudio (group[v], region, formats))
                regions.push_back (std::move (region));

            ++done;
        }
    }

    return {};
}

void SampleLibrary::buildLookup()
{
    lookup.assign (128 * 128, -1);

    for (int note = 0; note < 128; ++note)
    {
        for (int vel = 0; vel < 128; ++vel)
        {
            int best = -1;
            int bestDistance = std::numeric_limits<int>::max();

            for (size_t r = 0; r < regions.size(); ++r)
            {
                const auto& region = regions[r];

                if (note < region.loKey || note > region.hiKey)
                    continue;

                if (vel < region.loVel || vel > region.hiVel)
                    continue;

                // prefer the sample whose root is closest, so stretching is minimal
                const int distance = std::abs (note - region.rootNote);

                if (distance < bestDistance)
                {
                    bestDistance = distance;
                    best = (int) r;
                }
            }

            lookup[(size_t) (note * 128 + vel)] = best;
        }
    }

    // any velocity with no zone falls back to the nearest one that exists
    for (int note = 0; note < 128; ++note)
    {
        for (int vel = 0; vel < 128; ++vel)
        {
            if (lookup[(size_t) (note * 128 + vel)] >= 0)
                continue;

            for (int offset = 1; offset < 128; ++offset)
            {
                const int lower = vel - offset, upper = vel + offset;

                if (lower >= 0 && lookup[(size_t) (note * 128 + lower)] >= 0)
                { lookup[(size_t) (note * 128 + vel)] = lookup[(size_t) (note * 128 + lower)]; break; }

                if (upper < 128 && lookup[(size_t) (note * 128 + upper)] >= 0)
                { lookup[(size_t) (note * 128 + vel)] = lookup[(size_t) (note * 128 + upper)]; break; }
            }
        }
    }
}

//==============================================================================
void SamplerEngine::prepare (double sampleRate, int)
{
    sr = sampleRate;
    reset();
}

void SamplerEngine::reset()
{
    for (auto& v : voices)
        v = Voice();

    pedal = soft = 0.0f;
}

SamplerEngine::Voice* SamplerEngine::findVoice (int midiNote)
{
    for (auto& v : voices)
        if (v.active && v.note == midiNote && v.held)
            return &v;

    for (auto& v : voices)
        if (! v.active)
            return &v;

    Voice* best = nullptr;
    float quietest = std::numeric_limits<float>::max();

    for (auto& v : voices)
    {
        if (v.held)
            continue;

        if (v.env < quietest) { quietest = v.env; best = &v; }
    }

    if (best != nullptr)
        return best;

    Voice* oldest = &voices[0];

    for (auto& v : voices)
        if (v.order < oldest->order)
            oldest = &v;

    return oldest;
}

void SamplerEngine::noteOn (int midiNote, float velocity)
{
    if (active == nullptr || active->isEmpty())
        return;

    if (velocity <= 0.0f)
    {
        noteOff (midiNote);
        return;
    }

    const int vel = jlimit (1, 127, roundToInt (velocity * 127.0f));
    const auto* region = active->find (midiNote, vel);

    if (region == nullptr)
        return;

    auto* voice = findVoice (midiNote);

    voice->region = region;
    voice->position = 0.0;
    voice->note = midiNote;
    voice->active = true;
    voice->held = true;
    voice->sustained = pedal >= 0.45f;
    voice->order = ++orderCounter;

    const double pitchRatio = std::pow (2.0, (midiNote - region->rootNote) / 12.0) * region->tuneRatio;
    voice->increment = pitchRatio * region->sourceRate / sr;

    // the library already carries its own velocity layers, so the Dynamics knob
    // only trims on top of them rather than applying the whole range again
    const float normalised = (float) (vel - region->loVel)
                           / (float) jmax (1, region->hiVel - region->loVel);
    const float layerGain = 0.62f + 0.38f * jlimit (0.0f, 1.0f, normalised);
    const float trimDb = (velocity - 1.0f) * dynamicRange * 0.30f;

    voice->gain = region->gain * layerGain * Decibels::decibelsToGain (trimDb)
                * (1.0f - 0.28f * soft);

    voice->env = 0.0f;
    voice->envTarget = 1.0f;

    const float attack = jmax (0.002f, region->attackSeconds);
    voice->attackCoef = 1.0f - std::exp (-1.0f / (float) (attack * sr));
    voice->releaseCoef = 1.0f - std::exp (-1.0f / (float) (jmax (0.02f, region->releaseSeconds * releaseScale) * sr));

    // Tone darkens with the soft pedal and with the knob, the same way the
    // modelled engine does, so switching source does not change the feel
    const float toneAmount = tone - 0.45f * soft;
    const double cutoff = jlimit (400.0, sr * 0.45, 20000.0 * std::pow (2.0, (double) toneAmount * 2.6));
    voice->toneCoef = (float) jlimit (0.02, 1.0, 1.0 - std::exp (-2.0 * MathConstants<double>::pi * cutoff / sr));
    voice->toneStateL = voice->toneStateR = 0.0f;
}

void SamplerEngine::noteOff (int midiNote)
{
    for (auto& v : voices)
    {
        if (v.active && v.held && v.note == midiNote)
        {
            v.held = false;

            if (pedal >= 0.45f)
                v.sustained = true;
            else
                v.envTarget = 0.0f;
        }
    }
}

void SamplerEngine::sustainPedal (float value)
{
    const float previous = pedal;
    pedal = jlimit (0.0f, 1.0f, value);

    if (previous >= 0.45f && pedal < 0.45f)
        for (auto& v : voices)
            if (v.active && ! v.held && v.sustained)
            { v.sustained = false; v.envTarget = 0.0f; }
}

void SamplerEngine::softPedal (float value) { soft = jlimit (0.0f, 1.0f, value); }

void SamplerEngine::allNotesOff()
{
    for (auto& v : voices)
        if (v.active && v.held)
        { v.held = false; if (pedal < 0.45f) v.envTarget = 0.0f; else v.sustained = true; }
}

void SamplerEngine::panic()
{
    for (auto& v : voices)
        v = Voice();
}

void SamplerEngine::render (float* left, float* right, int numSamples)
{
    if (libraryDirty.exchange (false))
    {
        // only a pointer swap: the previous library stays alive in the processor
        for (auto& v : voices)
            v = Voice();

        active = pending;
    }

    if (active == nullptr || active->isEmpty())
        return;

    for (auto& v : voices)
    {
        if (! v.active || v.region == nullptr)
            continue;

        const auto& region = *v.region;
        const int length = region.audio.getNumSamples();
        const auto* srcL = region.audio.getReadPointer (0);
        const auto* srcR = region.audio.getNumChannels() > 1 ? region.audio.getReadPointer (1) : srcL;

        double position = v.position;
        float env = v.env;
        float toneL = v.toneStateL, toneR = v.toneStateR;
        const bool filtering = v.toneCoef < 0.999f;

        for (int n = 0; n < numSamples; ++n)
        {
            if (region.loops && position >= (double) region.loopEnd)
                position -= (double) (region.loopEnd - region.loopStart);

            if (position >= (double) (length - 2))
            {
                v.active = false;
                break;
            }

            const int i = (int) position;
            const float t = (float) (position - (double) i);

            const int im1 = jmax (0, i - 1);
            const int i1 = jmin (length - 1, i + 1);
            const int i2 = jmin (length - 1, i + 2);

            // 4 point Catmull-Rom: cheap and clean enough that stretching a
            // sample a few semitones does not add audible grit
            auto interpolate = [t] (float xm1, float x0, float x1, float x2)
            {
                const float c1 = 0.5f * (x1 - xm1);
                const float c2 = xm1 - 2.5f * x0 + 2.0f * x1 - 0.5f * x2;
                const float c3 = 0.5f * (x2 - xm1) + 1.5f * (x0 - x1);
                return ((c3 * t + c2) * t + c1) * t + x0;
            };

            float sampleL = interpolate (srcL[im1], srcL[i], srcL[i1], srcL[i2]);
            float sampleR = interpolate (srcR[im1], srcR[i], srcR[i1], srcR[i2]);

            const float coef = v.envTarget > 0.5f ? v.attackCoef : v.releaseCoef;
            env += coef * (v.envTarget - env);

            if (v.envTarget <= 0.0f && env < 1.0e-4f)
            {
                v.active = false;
                break;
            }

            if (filtering)
            {
                toneL += v.toneCoef * (sampleL - toneL);
                toneR += v.toneCoef * (sampleR - toneR);
                sampleL = toneL;
                sampleR = toneR;
            }

            const float g = env * v.gain;
            left[n]  += sampleL * g;
            right[n] += sampleR * g;

            position += v.increment;
        }

        v.position = position;
        v.env = env;
        v.toneStateL = toneL;
        v.toneStateR = toneR;
    }
}

} // namespace wp
