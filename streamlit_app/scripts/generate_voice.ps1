Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$text = "Hello there. This is a sample audio file featuring spoken words. We are generating this audio so that you can test the annotation platform with realistic voice data. The transcript will contain these exact words, broken down into segments, allowing you to test the synchronization between the audio waveform and the text editor. Thank you for testing."
$synth.SetOutputToWaveFile("C:\Users\Pardhu\Downloads\Akshara-Annotation-Platform-main\assets\audio\voice_sample.wav")
$synth.Speak($text)
$synth.Dispose()
