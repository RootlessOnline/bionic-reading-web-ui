'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { 
  Upload, 
  Download, 
  FileText, 
  Settings, 
  Eye, 
  Loader2, 
  CheckCircle2, 
  AlertCircle,
  BookOpen,
  Sparkles,
  Info,
  Zap
} from 'lucide-react'

interface ProcessingState {
  status: 'idle' | 'uploading' | 'processing' | 'complete' | 'error'
  progress: number
  message: string
  fileId?: string
  fileName?: string
  statistics?: {
    pages?: number
    text_blocks?: number
    estimated_words?: number
  }
  error?: string
}

interface PreviewState {
  original: string
  transformed: string
  loading: boolean
}

const SAMPLE_TEXT = `Bionic reading is a revolutionary method designed to enhance reading speed and comprehension. By highlighting the initial letters or syllables of words, this technique guides the reader's eye through the text more efficiently. This approach is particularly beneficial for individuals with ADHD, dyslexia, or other attention-related challenges.

The science behind bionic reading is based on how our brains process text. When we read, our eyes don't move smoothly across the page – they make quick jumps called saccades. By emphasizing the beginning of each word, bionic reading helps the brain anticipate and process text more quickly.`

export default function Home() {
  const [file, setFile] = useState<File | null>(null)
  const [emphasisRatio, setEmphasisRatio] = useState(40)
  const [minWordLength, setMinWordLength] = useState(3)
  const [boldIntensity, setBoldIntensity] = useState<'light' | 'medium' | 'heavy'>('medium')
  const [preserveLayout, setPreserveLayout] = useState(true)
  const [processing, setProcessing] = useState<ProcessingState>({
    status: 'idle',
    progress: 0,
    message: ''
  })
  const [preview, setPreview] = useState<PreviewState>({
    original: SAMPLE_TEXT,
    transformed: '',
    loading: false
  })
  const [activeTab, setActiveTab] = useState('upload')
  
  const fileInputRef = useRef<HTMLInputElement>(null)
  const dragRef = useRef<HTMLDivElement>(null)

  const handleFileSelect = useCallback((selectedFile: File) => {
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile)
      setProcessing({ status: 'idle', progress: 0, message: '' })
    }
  }, [])

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (dragRef.current) {
      dragRef.current.classList.add('border-primary', 'bg-primary/5')
    }
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (dragRef.current) {
      dragRef.current.classList.remove('border-primary', 'bg-primary/5')
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (dragRef.current) {
      dragRef.current.classList.remove('border-primary', 'bg-primary/5')
    }
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile) {
      handleFileSelect(droppedFile)
    }
  }, [handleFileSelect])

  const handleProcess = async () => {
    if (!file) return

    setProcessing({
      status: 'uploading',
      progress: 10,
      message: 'Uploading file...'
    })

    const formData = new FormData()
    formData.append('file', file)
    formData.append('emphasisRatio', (emphasisRatio / 100).toString())
    formData.append('minWordLength', minWordLength.toString())
    formData.append('boldIntensity', boldIntensity)
    formData.append('preserveLayout', preserveLayout.toString())

    try {
      setProcessing({
        status: 'processing',
        progress: 30,
        message: 'Processing PDF...'
      })

      const response = await fetch('/api/process', {
        method: 'POST',
        body: formData
      })

      const result = await response.json()

      if (result.success) {
        setProcessing({
          status: 'complete',
          progress: 100,
          message: 'Processing complete!',
          fileId: result.fileId,
          fileName: result.fileName,
          statistics: result.statistics
        })
      } else {
        setProcessing({
          status: 'error',
          progress: 0,
          message: result.error || 'Processing failed',
          error: result.error
        })
      }
    } catch (error) {
      setProcessing({
        status: 'error',
        progress: 0,
        message: 'Network error occurred',
        error: error instanceof Error ? error.message : 'Unknown error'
      })
    }
  }

  const handleDownload = async () => {
    if (!processing.fileId) return

    try {
      const response = await fetch(`/api/download/${processing.fileId}`)
      if (!response.ok) throw new Error('Download failed')
      
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = processing.fileName || 'bionic_enhanced.pdf'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Download error:', error)
    }
  }

  const generatePreview = useCallback(async () => {
    setPreview(prev => ({ ...prev, loading: true }))
    
    try {
      const response = await fetch('/api/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: preview.original,
          emphasisRatio: emphasisRatio / 100,
          minWordLength,
          boldIntensity
        })
      })

      const result = await response.json()
      
      if (result.success) {
        setPreview(prev => ({
          ...prev,
          transformed: result.transformed
        }))
      }
    } catch (error) {
      console.error('Preview error:', error)
    } finally {
      setPreview(prev => ({ ...prev, loading: false }))
    }
  }, [emphasisRatio, minWordLength, boldIntensity, preview.original])

  useEffect(() => {
    const timer = setTimeout(() => {
      generatePreview()
    }, 300)
    return () => clearTimeout(timer)
  }, [generatePreview])

  const formatTransformedText = (text: string) => {
    return text.split(/\*\*(.+?)\*\*/g).map((part, index) => {
      if (index % 2 === 1) {
        return <strong key={index} className="font-bold text-primary">{part}</strong>
      }
      return <span key={index}>{part}</span>
    })
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      <a 
        href="#main-content" 
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 bg-primary text-primary-foreground px-4 py-2 rounded-md z-50"
      >
        Skip to main content
      </a>

      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <header className="text-center mb-12">
          <div className="flex items-center justify-center gap-3 mb-4">
            <BookOpen className="h-10 w-10 text-primary" />
            <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-primary via-blue-600 to-indigo-600 bg-clip-text text-transparent">
              Bionic Reading Converter
            </h1>
          </div>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Transform your PDFs with bionic reading enhancements. Designed to improve reading speed 
            and comprehension for individuals with ADHD.
          </p>
          <div className="flex items-center justify-center gap-4 mt-4">
            <Badge variant="secondary" className="flex items-center gap-1">
              <Zap className="h-3 w-3" />
              <span>Up to 25% Faster Reading</span>
            </Badge>
          </div>
        </header>

        <div id="main-content" className="grid lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-1 h-fit sticky top-4">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                <span>Settings</span>
              </CardTitle>
              <CardDescription>
                Adjust the bionic reading parameters
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label htmlFor="emphasis-ratio">Emphasis Ratio</Label>
                  <Badge variant="outline">{emphasisRatio}%</Badge>
                </div>
                <Slider
                  id="emphasis-ratio"
                  min={20}
                  max={60}
                  step={5}
                  value={[emphasisRatio]}
                  onValueChange={(value) => setEmphasisRatio(value[0])}
                />
                <p className="text-xs text-muted-foreground">
                  How much of each word is bolded
                </p>
              </div>

              <div className="space-y-3">
                <Label htmlFor="min-word-length">Minimum Word Length</Label>
                <Input
                  id="min-word-length"
                  type="number"
                  min={1}
                  max={10}
                  value={minWordLength}
                  onChange={(e) => setMinWordLength(parseInt(e.target.value) || 3)}
                />
              </div>

              <div className="space-y-3">
                <Label htmlFor="bold-intensity">Bold Intensity</Label>
                <Select
                  value={boldIntensity}
                  onValueChange={(value: 'light' | 'medium' | 'heavy') => setBoldIntensity(value)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="light">Light</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="heavy">Heavy</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center justify-between">
                <Label htmlFor="preserve-layout">Preserve Layout</Label>
                <Switch
                  id="preserve-layout"
                  checked={preserveLayout}
                  onCheckedChange={setPreserveLayout}
                />
              </div>

              <Separator />

              <Alert>
                <Info className="h-4 w-4" />
                <AlertTitle className="text-sm">Tips</AlertTitle>
                <AlertDescription className="text-xs">
                  <ul className="space-y-1 mt-2">
                    <li>• Start with 40% emphasis ratio</li>
                    <li>• Try &quot;medium&quot; intensity first</li>
                    <li>• Adjust based on comfort</li>
                  </ul>
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>

          <div className="lg:col-span-2 space-y-6">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="upload" className="flex items-center gap-2">
                  <Upload className="h-4 w-4" />
                  Upload PDF
                </TabsTrigger>
                <TabsTrigger value="preview" className="flex items-center gap-2">
                  <Eye className="h-4 w-4" />
                  Preview
                </TabsTrigger>
              </TabsList>

              <TabsContent value="upload" className="mt-6">
                <Card>
                  <CardContent className="pt-6">
                    <div
                      ref={dragRef}
                      onDragEnter={handleDragEnter}
                      onDragLeave={handleDragLeave}
                      onDragOver={(e) => e.preventDefault()}
                      onDrop={handleDrop}
                      className="border-2 border-dashed border-muted-foreground/25 rounded-xl p-12 text-center transition-all cursor-pointer hover:border-primary hover:bg-primary/5"
                      role="button"
                      tabIndex={0}
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept=".pdf"
                        onChange={(e) => {
                          const f = e.target.files?.[0]
                          if (f) handleFileSelect(f)
                        }}
                        className="hidden"
                      />
                      
                      {file ? (
                        <div className="space-y-4">
                          <FileText className="h-16 w-16 mx-auto text-primary" />
                          <div>
                            <p className="font-semibold text-lg">{file.name}</p>
                            <p className="text-sm text-muted-foreground">
                              {(file.size / 1024 / 1024).toFixed(2)} MB
                            </p>
                          </div>
                          <Button variant="outline" size="sm" onClick={(e) => {
                            e.stopPropagation()
                            setFile(null)
                          }}>
                            Choose different file
                          </Button>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          <Upload className="h-16 w-16 mx-auto text-muted-foreground" />
                          <div>
                            <p className="font-semibold text-lg">Drop your PDF here</p>
                            <p className="text-sm text-muted-foreground">or click to browse</p>
                          </div>
                        </div>
                      )}
                    </div>

                    {processing.status !== 'idle' && (
                      <div className="mt-6 space-y-4">
                        <Separator />
                        <div className="space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium">{processing.message}</span>
                            {processing.status === 'processing' && (
                              <Loader2 className="h-4 w-4 animate-spin text-primary" />
                            )}
                          </div>
                          <Progress value={processing.progress} />
                        </div>

                        {processing.status === 'complete' && (
                          <Alert className="border-green-200 bg-green-50">
                            <CheckCircle2 className="h-4 w-4 text-green-600" />
                            <AlertTitle className="text-green-800">Complete!</AlertTitle>
                            <AlertDescription className="text-green-700">
                              <Button onClick={handleDownload} className="mt-2" size="sm">
                                <Download className="h-4 w-4 mr-2" />
                                Download Enhanced PDF
                              </Button>
                            </AlertDescription>
                          </Alert>
                        )}

                        {processing.status === 'error' && (
                          <Alert variant="destructive">
                            <AlertCircle className="h-4 w-4" />
                            <AlertTitle>Error</AlertTitle>
                            <AlertDescription>{processing.error}</AlertDescription>
                          </Alert>
                        )}
                      </div>
                    )}

                    {file && processing.status === 'idle' && (
                      <div className="mt-6 flex justify-center">
                        <Button size="lg" onClick={handleProcess} className="px-8">
                          <Sparkles className="h-5 w-5 mr-2" />
                          Transform with Bionic Reading
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="preview" className="mt-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Live Preview</CardTitle>
                    <CardDescription>See how bionic reading transforms text</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid md:grid-cols-2 gap-6">
                      <div className="space-y-3">
                        <h3 className="font-semibold">Original Text</h3>
                        <div className="h-64 overflow-auto rounded-lg border bg-muted/30 p-4">
                          <p className="text-sm leading-relaxed">{preview.original}</p>
                        </div>
                      </div>
                      <div className="space-y-3">
                        <h3 className="font-semibold">Bionic Enhanced</h3>
                        <div className="h-64 overflow-auto rounded-lg border bg-primary/5 p-4">
                          {preview.loading ? (
                            <div className="flex items-center justify-center h-full">
                              <Loader2 className="h-6 w-6 animate-spin text-primary" />
                            </div>
                          ) : (
                            <p className="text-sm leading-relaxed">
                              {formatTransformedText(preview.transformed)}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>
    </main>
  )
}
