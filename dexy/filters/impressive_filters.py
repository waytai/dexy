from dexy.dexy_filter import DexyFilter
import os
import re
import subprocess
import wave

class ImpressiveFilter(DexyFilter):
    ALIASES = ['impressive']
    INPUT_EXTENSIONS = [".tex"]
    OUTPUT_EXTENSIONS = [".tex"]

    def process_text(self, input_text):
        page_number = 0
        page_info = {}

        page_info_artifact = self.artifact.add_additional_artifact(self.artifact.canonical_filename().replace(".tex", ".pdf") + ".info", ".info")

        for l in self.artifact.input_text().splitlines():
            if re.search("^\s*(\\\\begin{frame}|\\\\pause)", l):
                page_number += 1
                page_info[page_number] = {}
            else:
                # TODO support the other commands from http://impressive.sourceforge.net/manual.php#scripts
                m = re.search("^%%(transition|timeout|speech):\s+(.+)$", l)
                if m:
                    command = m.groups()[0]
                    value = m.groups()[1]
                    if command == 'speech':
                        wav_filename = "speech-page-%04d.wav" % page_number
                        wav_key_with_ext = os.path.join(self.artifact.canonical_dir(), wav_filename)
                        wav_artifact = self.artifact.add_additional_artifact(wav_key_with_ext, ".wav")
                        proc = subprocess.Popen("espeak -v en-us -w %s" % wav_artifact.filepath(),
                                shell=True,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

                        stdout, stderr = proc.communicate(value)
                        page_info[page_number]['sound'] = wav_filename
                        wav = wave.open(wav_artifact.filepath())

                        # Calculate timeout automatically from length of sound file.
                        # Need to specify manual timeout before this to override.
                        if not page_info[page_number].has_key('timeout'):
                            timeout = float(wav.getnframes()) / wav.getframerate() * 1000
                            page_info[page_number]['timeout'] = int(timeout)

                        wav.close()

                    elif command in ('timeout', 'transition'):
                        # get rid of unicode
                        page_info[page_number][str(command)] = str(value)
                    else:
                        raise Exception("unknown command '%s'" % command)

        with open(page_info_artifact.filepath(), "w") as f:
            f.write("PageProps = {\n")
            n = len(page_info.keys())
            for i, k in enumerate(sorted(page_info)):
                if i == 0:
                    f.write("  %s: {\n" % k)
                if i > 0:
                    f.write("  }")
                    if i < n-1:
                        f.write(",\n  %s: {\n" % k)

                nn = len(page_info[k].keys())
                for ii, kk in enumerate(page_info[k].keys()):
                    if kk in ('transition', 'timeout'):
                        f.write("    '%s': %s" % (kk, page_info[k][kk]))
                    else:
                        f.write("    '%s': '%s'" % (kk, page_info[k][kk]))

                    if ii < nn-1:
                        f.write(",\n")
                    else:
                        f.write("\n")

            f.write("}\n")

        return input_text
