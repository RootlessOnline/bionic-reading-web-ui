'use client'

import { useState, useCallback, useRef, useEffect } from 'react'

export default function Home() {
  const [file, setFile] = useState<File | null>(null)
  const [emphasisRatio, setEmphasisRatio] = useState(40)
  const [minWordLength, setMinWordLength] = useState(3)
  const [boldIntensity, setBoldIntensity] = useState<'light' | 'medium' | 'heavy'>('medium')
  const [processing, setProcessing] = useState({
    status: 'idle' as 'idle' | 'uploading' | 'processing' | 'complete' | 'error',
    progress: 0,
    message: '',
    fileId: '',
    fileName: '',
    error: ''
  })
  const [preview, setPreview] = useState({
    original: 'Bionic reading helps improve reading speed by highlighting the beginning of words. This guides your eyes through the text more efficiently.',
    transformed: '',
    loading: false
  })
  const [activeTab, setActiveTab] = useState('upload')
  
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = useCallback((selectedFile: File) => {
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile)
      setProcessing({ status: 'idle', progress: 0, message: '', fileId: '', fileName: '', error: '' })
    }
  }, [])

  const handleProcess = async () => {
    if (!file) return

    setProcessing({ status: 'uploading', progress: 10, message: 'Uploading file...', fileId: '', fileName: '', error: '' })

    const formData = new FormData()
    formData.append('file', file)
    formData.append('emphasisRatio', (emphasisRatio / 100).toString())
    formData.append('minWordLength', minWordLength.toString())
    formData.append('boldIntensity', boldIntensity)

    try {
      setProcessing(prev => ({ ...prev, status: 'processing', progress: 30, message: 'Processing PDF...' }))

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
          error: ''
        })
      } else {
        setProcessing(prev => ({ ...prev, status: 'error', progress: 0, message: result.error || 'Processing failed', error: result.error }))
      }
    } catch (error) {
      setProcessing(prev => ({ 
        ...prev, 
        status: 'error', 
        progress: 0, 
        message: 'Network error', 
        error: error instanceof Error ? error.message : 'Unknown error' 
      }))
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
        setPreview(prev => ({ ...prev, transformed: result.transformed }))
      }
    } catch (error) {
      console.error('Preview error:', error)
    } finally {
      setPreview(prev => ({ ...prev, loading: false }))
    }
  }, [emphasisRatio, minWordLength, boldIntensity, preview.original])

  useEffect(() => {
    generatePreview()
  }, [generatePreview])

  const formatTransformedText = (text: string) => {
    return text.split(/\*\*(.+?)\*\*/g).map((part, index) => {
      if (index % 2 === 1) {
        return <strong key={index} style={{ fontWeight: 700, color: '#2563eb' }}>{part}</strong>
      }
      return <span key={index}>{part}</span>
    })
  }

  return (
    <main style={{ minHeight: '100vh', background: 'linear-gradient(to bottom right, #f8fafc, #eff6ff, #eef2ff)' }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem' }}>
        <header style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h1 style={{ fontSize: '2.5rem', fontWeight: 'bold', background: 'linear-gradient(to right, #2563eb, #7c3aed)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            📚 Bionic Reading Converter
          </h1>
          <p style={{ color: '#64748b', marginTop: '0.5rem' }}>
            Transform PDFs for faster reading - optimized for ADHD readers
          </p>
        </header>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
          {/* Settings Panel */}
          <div style={{ 
            background: 'white', 
            borderRadius: '0.75rem', 
            padding: '1.5rem',
            boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)'
          }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem' }}>⚙️ Settings</h2>
            
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', fontWeight: '500', marginBottom: '0.5rem' }}>
                Emphasis Ratio: {emphasisRatio}%
              </label>
              <input
                type="range"
                min="20"
                max="60"
                step="5"
                value={emphasisRatio}
                onChange={(e) => setEmphasisRatio(parseInt(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', fontWeight: '500', marginBottom: '0.5rem' }}>
                Min Word Length
              </label>
              <input
                type="number"
                min="1"
                max="10"
                value={minWordLength}
                onChange={(e) => setMinWordLength(parseInt(e.target.value) || 3)}
                style={{ width: '100%', padding: '0.5rem', border: '1px solid #d1d5db', borderRadius: '0.5rem' }}
              />
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', fontWeight: '500', marginBottom: '0.5rem' }}>
                Bold Intensity
              </label>
              <select
                value={boldIntensity}
                onChange={(e) => setBoldIntensity(e.target.value as 'light' | 'medium' | 'heavy')}
                style={{ width: '100%', padding: '0.5rem', border: '1px solid #d1d5db', borderRadius: '0.5rem' }}
              >
                <option value="light">Light</option>
                <option value="medium">Medium</option>
                <option value="heavy">Heavy</option>
              </select>
            </div>

            <div style={{ 
              background: '#eff6ff', 
              padding: '0.75rem', 
              borderRadius: '0.5rem',
              fontSize: '0.875rem',
              color: '#1e40af'
            }}>
              💡 Start with 40% ratio and medium intensity
            </div>
          </div>

          {/* Main Content */}
          <div style={{ 
            background: 'white', 
            borderRadius: '0.75rem', 
            padding: '1.5rem',
            boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)'
          }}>
            {/* Tabs */}
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
              <button
                onClick={() => setActiveTab('upload')}
                style={{
                  flex: 1,
                  padding: '0.75rem',
                  background: activeTab === 'upload' ? '#2563eb' : '#f1f5f9',
                  color: activeTab === 'upload' ? 'white' : '#1e293b',
                  border: 'none',
                  borderRadius: '0.5rem',
                  cursor: 'pointer',
                  fontWeight: '500'
                }}
              >
                📤 Upload PDF
              </button>
              <button
                onClick={() => setActiveTab('preview')}
                style={{
                  flex: 1,
                  padding: '0.75rem',
                  background: activeTab === 'preview' ? '#2563eb' : '#f1f5f9',
                  color: activeTab === 'preview' ? 'white' : '#1e293b',
                  border: 'none',
                  borderRadius: '0.5rem',
                  cursor: 'pointer',
                  fontWeight: '500'
                }}
              >
                👁️ Preview
              </button>
            </div>

            {activeTab === 'upload' && (
              <div>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  style={{
                    border: '2px dashed #94a3b8',
                    borderRadius: '0.75rem',
                    padding: '3rem',
                    textAlign: 'center',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf"
                    onChange={(e) => {
                      const f = e.target.files?.[0]
                      if (f) handleFileSelect(f)
                    }}
                    style={{ display: 'none' }}
                  />
                  
                  {file ? (
                    <div>
                      <p style={{ fontWeight: '600', fontSize: '1.125rem' }}>📄 {file.name}</p>
                      <p style={{ color: '#64748b', fontSize: '0.875rem' }}>
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                      <button
                        onClick={(e) => { e.stopPropagation(); setFile(null) }}
                        style={{
                          marginTop: '0.5rem',
                          padding: '0.5rem 1rem',
                          background: '#f1f5f9',
                          border: 'none',
                          borderRadius: '0.5rem',
                          cursor: 'pointer'
                        }}
                      >
                        Choose different file
                      </button>
                    </div>
                  ) : (
                    <div>
                      <p style={{ fontWeight: '600', fontSize: '1.125rem' }}>Drop your PDF here</p>
                      <p style={{ color: '#64748b', fontSize: '0.875rem' }}>or click to browse</p>
                    </div>
                  )}
                </div>

                {processing.status !== 'idle' && (
                  <div style={{ marginTop: '1rem' }}>
                    <p style={{ fontWeight: '500', marginBottom: '0.5rem' }}>{processing.message}</p>
                    <div style={{ background: '#e2e8f0', borderRadius: '0.5rem', overflow: 'hidden' }}>
                      <div style={{ 
                        height: '8px', 
                        background: '#2563eb',
                        width: `${processing.progress}%`,
                        transition: 'width 0.3s'
                      }} />
                    </div>
                  </div>
                )}

                {processing.status === 'complete' && (
                  <div style={{ marginTop: '1rem', padding: '1rem', background: '#dcfce7', borderRadius: '0.5rem' }}>
                    <p style={{ color: '#166534', fontWeight: '500' }}>✅ Processing complete!</p>
                    <button
                      onClick={handleDownload}
                      style={{
                        marginTop: '0.5rem',
                        padding: '0.5rem 1rem',
                        background: '#2563eb',
                        color: 'white',
                        border: 'none',
                        borderRadius: '0.5rem',
                        cursor: 'pointer',
                        fontWeight: '500'
                      }}
                    >
                      📥 Download Enhanced PDF
                    </button>
                  </div>
                )}

                {processing.status === 'error' && (
                  <div style={{ marginTop: '1rem', padding: '1rem', background: '#fee2e2', borderRadius: '0.5rem' }}>
                    <p style={{ color: '#991b1b' }}>❌ {processing.error}</p>
                  </div>
                )}

                {file && processing.status === 'idle' && (
                  <button
                    onClick={handleProcess}
                    style={{
                      width: '100%',
                      marginTop: '1rem',
                      padding: '0.75rem',
                      background: 'linear-gradient(to right, #2563eb, #7c3aed)',
                      color: 'white',
                      border: 'none',
                      borderRadius: '0.5rem',
                      cursor: 'pointer',
                      fontWeight: '600',
                      fontSize: '1rem'
                    }}
                  >
                    ✨ Transform with Bionic Reading
                  </button>
                )}
              </div>
            )}

            {activeTab === 'preview' && (
              <div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                  <div>
                    <h3 style={{ fontWeight: '600', marginBottom: '0.5rem' }}>Original</h3>
                    <div style={{ 
                      height: '200px', 
                      overflow: 'auto', 
                      background: '#f8fafc', 
                      padding: '1rem',
                      borderRadius: '0.5rem',
                      border: '1px solid #e2e8f0'
                    }}>
                      <p style={{ fontSize: '0.875rem', lineHeight: 1.7 }}>{preview.original}</p>
                    </div>
                  </div>
                  <div>
                    <h3 style={{ fontWeight: '600', marginBottom: '0.5rem' }}>Bionic Enhanced</h3>
                    <div style={{ 
                      height: '200px', 
                      overflow: 'auto', 
                      background: '#eff6ff', 
                      padding: '1rem',
                      borderRadius: '0.5rem',
                      border: '1px solid #bfdbfe'
                    }}>
                      {preview.loading ? (
                        <p style={{ textAlign: 'center', color: '#64748b' }}>Loading...</p>
                      ) : (
                        <p style={{ fontSize: '0.875rem', lineHeight: 1.7 }}>
                          {formatTransformedText(preview.transformed)}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <footer style={{ textAlign: 'center', marginTop: '2rem', color: '#64748b', fontSize: '0.875rem' }}>
          Designed for readers with ADHD • Optimized for accessibility
        </footer>
      </div>
    </main>
  )
}
