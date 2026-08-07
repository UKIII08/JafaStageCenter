#pragma once

#include <juce_core/juce_core.h>
#include <juce_events/juce_events.h>

/*
    The link to Jafa Stage Center.

    The app running the service knows which song is up, what tempo it is and
    what key it is in. The piano does not, and on a stage nobody has a spare
    hand to tell it. So the app leaves that on disk and the plugin reads it.

    A file rather than a socket, deliberately. Both ends run on the same
    machine - that is the whole premise - and a file needs no port, no firewall
    prompt in the middle of a service, and no networking in an audio plugin. It
    also survives either side restarting, which a socket does not: the app can
    be closed and reopened mid-set and the piano simply keeps reading.

    The app writes:

        %APPDATA%\Jafa Stage\Worship Piano\live.json      (Windows)
        ~/Library/Application Support/Jafa Stage/...      (macOS)
        ~/.config/Jafa Stage/Worship Piano/live.json      (Linux)

        { "song_id": 12, "title": "...", "key": "D", "bpm": 74,
          "preset": "Niedziela filc", "updated": 1770000000 }

    and the plugin writes plugin.json back, so the app can offer the presets
    that actually exist rather than a free text box.

    Polling, not a file watcher: five times a second costs nothing next to
    audio, and the platform watch APIs each fail differently over the network
    shares and synced folders people keep their things in.
*/
namespace wp
{

class StageLink : private juce::Timer
{
public:
    StageLink();
    ~StageLink() override;

    struct Song
    {
        int id = -1;
        juce::String title, key, preset;
        double bpm = 0.0;

        bool isValid() const noexcept { return id >= 0 || title.isNotEmpty(); }
    };

    /** Called on the message thread when the app moves to a different song. */
    std::function<void (const Song&)> onSongChanged;

    /** Whatever the app last said. Safe to call from any thread. */
    Song getSong() const;

    /** True when live.json has been seen at all this session. */
    bool isConnected() const noexcept { return connected.load(); }

    /** The folder both sides share; also where the presets live. */
    static juce::File sharedDirectory();

    /*  Tells the app which presets exist and what is loaded, so the song editor
        can offer a list instead of asking someone to spell a preset name.
    */
    static void publishState (const juce::StringArray& presetNames,
                              const juce::String& currentPreset,
                              const juce::String& libraryPath);

private:
    void timerCallback() override;
    void readFile();

    juce::File liveFile;
    juce::int64 lastModified = 0;
    juce::int64 lastSize = -1;

    mutable juce::CriticalSection lock;
    Song song;

    std::atomic<bool> connected { false };

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (StageLink)
};

} // namespace wp
