#include "StageLink.h"

using namespace juce;

namespace wp
{

StageLink::StageLink()
{
    liveFile = sharedDirectory().getChildFile ("live.json");

    // read once up front, so opening the plugin mid-set lands on the song that
    // is already up rather than waiting for the next one
    readFile();

    startTimer (200);
}

StageLink::~StageLink()
{
    stopTimer();
}

File StageLink::sharedDirectory()
{
    auto dir = File::getSpecialLocation (File::userApplicationDataDirectory)
                   .getChildFile ("Jafa Stage")
                   .getChildFile ("Worship Piano");

    if (! dir.exists())
        dir.createDirectory();

    return dir;
}

StageLink::Song StageLink::getSong() const
{
    const ScopedLock sl (lock);
    return song;
}

void StageLink::timerCallback()
{
    readFile();
}

void StageLink::readFile()
{
    if (! liveFile.existsAsFile())
        return;

    /*  Size as well as time. A song change can land inside the same second the
        last one did - two clicks in a row while finding the right verse - and a
        second is a long time to be playing the wrong sound.
    */
    const auto modified = liveFile.getLastModificationTime().toMilliseconds();
    const auto size = liveFile.getSize();

    if (modified == lastModified && size == lastSize)
        return;

    lastModified = modified;
    lastSize = size;

    const auto parsed = JSON::parse (liveFile.loadFileAsString());

    if (! parsed.isObject())
        return;     // a half written file: the next poll gets the whole one

    Song incoming;
    incoming.id     = (int) parsed.getProperty ("song_id", -1);
    incoming.title  = parsed.getProperty ("title", "").toString();
    incoming.key    = parsed.getProperty ("key", "").toString();
    incoming.preset = parsed.getProperty ("preset", "").toString();
    incoming.bpm    = (double) parsed.getProperty ("bpm", 0.0);

    connected = true;

    bool changed = false;

    {
        const ScopedLock sl (lock);

        /*  Only the things that drive a sound count as a change. The app rewrites
            this file on every slide, and on the blackout button, not just when a
            song comes up - reloading a preset because a verse scrolled would
            throw away whatever the player had just reached over and adjusted.

            Title and key are stored for the display either way; they never
            trigger anything.
        */
        changed = incoming.id != song.id
               || incoming.preset != song.preset
               || std::abs (incoming.bpm - song.bpm) > 0.01;

        song = incoming;
    }

    if (changed && onSongChanged != nullptr)
        onSongChanged (incoming);
}

void StageLink::publishState (const StringArray& presetNames,
                              const String& currentPreset,
                              const String& libraryPath)
{
    DynamicObject::Ptr root (new DynamicObject());

    Array<var> names;

    for (const auto& n : presetNames)
        names.add (n);

    root->setProperty ("presets", names);
    root->setProperty ("current", currentPreset);
    root->setProperty ("library", libraryPath);
    root->setProperty ("updated", Time::currentTimeMillis() / 1000);

    /*  Written beside itself and moved into place, so the app never reads a file
        that is half a preset list. A rename on the same volume is atomic
        everywhere this runs.
    */
    auto target = sharedDirectory().getChildFile ("plugin.json");
    auto temp = target.getSiblingFile ("plugin.json.tmp");

    if (temp.replaceWithText (JSON::toString (var (root.get()))))
    {
        target.deleteFile();

        if (! temp.moveFileTo (target))
            temp.deleteFile();
    }
}

} // namespace wp
