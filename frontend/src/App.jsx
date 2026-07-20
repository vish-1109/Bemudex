import { useState, useEffect, useCallback, useRef, useMemo, memo } from 'react';
import {
  Music, Video, Download, AlertTriangle, Trash2, FolderOpen, X,
  Play, RefreshCw, Link, ChevronDown, ChevronUp, ChevronLeft, ChevronRight,
  CheckCircle2, Home, History as HistoryIcon, Settings as SettingsIcon,
  Search, HardDrive, Zap, Shield, ListMusic,
  Clipboard, Check, MonitorPlay, Headphones, EyeOff, Info, AlertCircle,
  Plus, Edit3, RotateCcw
} from 'lucide-react';
import './App.css';
import { NotificationManager } from './notification_manager';

/* ─── API BRIDGE ─── */
const callApi = async (methodName, ...args) => {
  if (window.pywebview?.api) {
    if (typeof window.pywebview.api[methodName] === 'function')
      return await window.pywebview.api[methodName](...args);
    const camel = methodName.replace(/_([a-z])/g, g => g[1].toUpperCase());
    if (typeof window.pywebview.api[camel] === 'function')
      return await window.pywebview.api[camel](...args);
    const snake = methodName.replace(/[A-Z]/g, l => `_${l.toLowerCase()}`);
    if (typeof window.pywebview.api[snake] === 'function')
      return await window.pywebview.api[snake](...args);
    throw new Error(`API method ${methodName} not found.`);
  }
  throw new Error("pywebview not ready");
};

/* ─── HELPERS ─── */
const formatViews = (n) => {
  if (!n) return '';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M views`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K views`;
  return `${n} views`;
};

const resolutionLabel = (h) => {
  const labels = { 4320: '8K', 2160: '4K', 1440: '1440p', 1080: '1080p', 720: '720p', 480: '480p', 360: '360p' };
  return labels[h] || `${h}p`;
};

const resolutionSublabel = (h) => {
  const labels = { 4320: 'FUHD', 2160: 'UHD', 1440: 'QHD', 1080: 'FHD', 720: 'HD', 480: 'SD', 360: 'SD' };
  return labels[h] || '';
};

/* Greeting is pure — computed once at module-top, not re-created per render */
const getGreeting = () => {
  const hr = new Date().getHours();
  if (hr < 12) return 'Good Morning';
  if (hr < 17) return 'Good Afternoon';
  return 'Good Evening';
};

/* ─── MEMOIZED COMPONENTS FOR PERFORMANCE ─── */
const DownloadCard = memo(({ item, onCancel, onRetry }) => {
  return (
    <div className="download-card">
      <div className="download-card-top">
        {item.thumbnail ? (
          <img className="download-card-thumb" src={item.thumbnail} alt="" aria-hidden="true" />
        ) : (
          <div className="download-card-thumb download-card-thumb-placeholder">
            {item.format === 'audio' ? <Music size={16} aria-hidden="true" /> : <Video size={16} aria-hidden="true" />}
          </div>
        )}
        <div className="download-card-info">
          <span className="download-card-title" title={item.title}>{item.title}</span>
          <span className="download-card-channel">{item.format === 'audio' ? 'MP3' : 'MP4'} • {item.quality || ''}</span>
        </div>
      </div>
      <div className="download-card-progress">
        <div className="progress-track">
          <div
            className={`progress-fill ${item.status === 'converting' ? 'converting' : item.status === 'failed' ? 'failed' : ''}`}
            style={{ width: `${item.status === 'converting' || item.status === 'failed' ? 100 : item.percent || 0}%` }}
          />
        </div>
      </div>
      <div className="download-card-stats">
        <span className={`download-card-stat-text ${item.status === 'failed' ? 'failed' : ''}`}>
          {item.status === 'converting' ? 'Processing...'
            : item.status === 'failed' ? (item.sizeInfo || 'Failed')
            : item.status === 'queued' ? 'Queued'
            : `${Math.round(item.percent || 0)}% • ${item.speed || ''} • ${item.sizeInfo || ''} • ETA ${item.eta || ''}`}
        </span>
        <div className="download-card-actions">
          {item.status === 'failed' && (
            <button className="download-action-btn retry" onClick={onRetry} title="Retry">
              <RotateCcw size={13} />
            </button>
          )}
          <button className="download-action-btn cancel" onClick={onCancel} title={item.status === 'failed' ? "Dismiss" : "Cancel"}>
            <X size={13} />
          </button>
        </div>
      </div>
    </div>
  );
});
DownloadCard.displayName = 'DownloadCard';

const CompletedCard = memo(({ item, onPlayFile, onOpenFolder }) => {
  return (
    <div className="completed-card">
      {item.thumbnail ? (
        <img className="completed-card-thumb" src={item.thumbnail} alt="" aria-hidden="true" />
      ) : (
        <div className="completed-card-thumb completed-card-thumb-placeholder">
          <CheckCircle2 size={14} aria-hidden="true" />
        </div>
      )}
      <div className="completed-card-info">
        <span className="completed-card-title" title={item.title}>{item.title}</span>
        <span className="completed-card-meta">
          {item.filePath ? item.filePath.split('.').pop().toUpperCase() : (item.format === 'audio' ? 'MP3' : 'MP4')} • {item.sizeInfo || 'Completed'}
        </span>
      </div>
      <div className="completed-card-actions">
        {item.filePath && (
          <>
            <button className="completed-action-btn" onClick={() => onPlayFile(item.filePath)} title="Play">
              <Play size={12} />
            </button>
            <button className="completed-action-btn" onClick={() => onOpenFolder(item.filePath)} title="Folder">
              <FolderOpen size={12} />
            </button>
          </>
        )}
      </div>
    </div>
  );
});
CompletedCard.displayName = 'CompletedCard';

/* ─────────────────────── APP ─────────────────────── */
function App() {

  // Navigation
  const [activePage, setActivePage] = useState('home');

  // URL & Metadata
  const [urlInput, setUrlInput] = useState('');
  const urlInputRef = useRef('');
  useEffect(() => {
    urlInputRef.current = urlInput;
  }, [urlInput]);
  const [metadata, setMetadata] = useState(null);
  const [metadataLoading, setMetadataLoading] = useState(false);
  const [metadataError, setMetadataError] = useState(null);

  // Format selection
  const [downloadType, setDownloadType] = useState('video');
  const [selectedResolution, setSelectedResolution] = useState('best');
  const [selectedAudioBitrate, setSelectedAudioBitrate] = useState('320');
  const [audioFormat, setAudioFormat] = useState('mp3');
  const [embedTags, setEmbedTags] = useState(true);
  const [embedChapters, setEmbedChapters] = useState(true);
  const lastFetchedUrlRef = useRef('');
  const scheduledTimerRef = useRef(null);
  const lastDownloadParamsRef = useRef(null);

  // Clipboard auto-detection
  const [clipboardUrl, setClipboardUrl] = useState('');
  const [showClipboardCard, setShowClipboardCard] = useState(false);

  // Bandwidth & Scheduler Settings
  const [bandwidthLimit, setBandwidthLimit] = useState(() => {
    const s = localStorage.getItem('bandwidthLimit');
    return s !== null ? parseInt(s, 10) : 0; // 0 = No Limit, in MB/s
  });
  const [scheduleEnabled, setScheduleEnabled] = useState(() => {
    const s = localStorage.getItem('scheduleEnabled');
    return s !== null ? JSON.parse(s) : false;
  });
  const [scheduleTime, setScheduleTime] = useState(() => {
    return localStorage.getItem('scheduleTime') || '23:00';
  });

  // Metadata editor overrides
  const [editedTitle, setEditedTitle] = useState('');
  const [editedArtist, setEditedArtist] = useState('');
  const [editedThumbnail, setEditedThumbnail] = useState('');
  const [customCoverFile, setCustomCoverFile] = useState(null);
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [isEditingArtist, setIsEditingArtist] = useState(false);

  // Folder
  const [folder, setFolder] = useState('');

  // Download states
  const [downloading, setDownloading] = useState(false);
  const [queue, setQueue] = useState([]);
  const [completed, setCompleted] = useState([]);
  const [showCompleted, setShowCompleted] = useState(true);

  // History
  const [history, setHistory] = useState([]);
  const [historySearch, setHistorySearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [historyFilter, setHistoryFilter] = useState('all');

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(historySearch);
    }, 200);
    return () => clearTimeout(handler);
  }, [historySearch]);

  // Settings
  const [dependencies, setDependencies] = useState({
    bemudex: { version: 'v2.0.2', build: '2026.07.20', release_channel: 'stable' },
    ytdlp: { version: '...', latestVersion: '', status: 'unknown', updateAvailable: false, checking: false, updating: false },
    ffmpeg: { installed: false, version: '', path: '', checking: false },
    folderWritable: false,
    status: 'attention_required',
    lastCheckedStr: ''
  });
  const [dependenciesLoaded, setDependenciesLoaded] = useState(false);
  const [diagnostics, setDiagnostics] = useState(null);
  const [showDiagnosticsModal, setShowDiagnosticsModal] = useState(false);
  const [loadingDiagnostics, setLoadingDiagnostics] = useState(false);
  const [showNotification, setShowNotification] = useState(() => {
    const s = localStorage.getItem('showNotification');
    return s !== null ? JSON.parse(s) : true;
  });
  const [embedThumbnail, setEmbedThumbnail] = useState(() => {
    const s = localStorage.getItem('embedThumbnail');
    return s !== null ? JSON.parse(s) : true;
  });
  const [autoUpdateCheck, setAutoUpdateCheck] = useState(() => {
    const s = localStorage.getItem('autoUpdateCheck');
    return s !== null ? JSON.parse(s) : true;
  });
  const [darkMode, setDarkMode] = useState(() => {
    const s = localStorage.getItem('darkMode');
    return s !== null ? JSON.parse(s) : true;
  });
  const [collapsed, setCollapsed] = useState(() => {
    const s = localStorage.getItem('sidebarCollapsed');
    return s !== null ? JSON.parse(s) : false;
  });
  const [panelWidth, setPanelWidth] = useState(() => {
    const w = localStorage.getItem('panelWidth');
    return w !== null ? parseInt(w, 10) : 340;
  });
  const [uiScale, setUiScale] = useState(() => {
    const s = localStorage.getItem('uiScale');
    return s !== null ? parseInt(s, 10) : 100;
  });

  // Storage
  const [storage, setStorage] = useState(null);

  // Tip
  const [showTip, setShowTip] = useState(() => {
    return localStorage.getItem('hideTip') !== 'true';
  });

  // In-app toast notifications (replaces alert/confirm)
  const [toasts, setToasts] = useState([]);
  const toastIdRef = useRef(0);
  const notifier = useMemo(() => new NotificationManager(setToasts, toastIdRef), []);
  const startupCheckedRef = useRef(false);

  const showToast = useCallback((message, type = 'info', duration = 4000) => {
    notifier.show(message, type, duration);
  }, [notifier]);

  // Confirm dialog state (replaces window.confirm)
  const [confirmDialog, setConfirmDialog] = useState(null);
  const showConfirm = useCallback((message, onConfirm) => {
    setConfirmDialog({ message, onConfirm });
  }, []);

  /* ─── SETTINGS PERSISTENCE ─── */
  useEffect(() => { localStorage.setItem('showNotification', JSON.stringify(showNotification)); }, [showNotification]);
  useEffect(() => { localStorage.setItem('embedThumbnail', JSON.stringify(embedThumbnail)); }, [embedThumbnail]);
  useEffect(() => { localStorage.setItem('autoUpdateCheck', JSON.stringify(autoUpdateCheck)); }, [autoUpdateCheck]);
  useEffect(() => { localStorage.setItem('darkMode', JSON.stringify(darkMode)); }, [darkMode]);
  useEffect(() => { localStorage.setItem('sidebarCollapsed', JSON.stringify(collapsed)); }, [collapsed]);
  useEffect(() => { localStorage.setItem('panelWidth', panelWidth.toString()); }, [panelWidth]);
  useEffect(() => {
    localStorage.setItem('bandwidthLimit', bandwidthLimit.toString());
  }, [bandwidthLimit]);
  useEffect(() => {
    localStorage.setItem('scheduleEnabled', JSON.stringify(scheduleEnabled));
  }, [scheduleEnabled]);
  useEffect(() => {
    localStorage.setItem('scheduleTime', scheduleTime);
  }, [scheduleTime]);

  useEffect(() => {
    localStorage.setItem('uiScale', uiScale.toString());
    document.documentElement.style.zoom = `${uiScale}%`;
  }, [uiScale]);

  // Clean up scheduled timer on unmount to prevent memory leaks
  useEffect(() => {
    return () => {
      if (scheduledTimerRef.current) {
        clearTimeout(scheduledTimerRef.current);
      }
    };
  }, []);

  // Clipboard focus listener
  useEffect(() => {
    let focusTimer = null;
    const checkClipboard = async () => {
      if (!window.pywebview?.api) return;
      try {
        const text = await callApi('get_clipboard_text');
        if (text && text.trim()) {
          const isUrl = text.includes('youtube.com/') || text.includes('youtu.be/');
          if (isUrl && text !== urlInputRef.current && text !== lastFetchedUrlRef.current) {
            setClipboardUrl(text);
            setShowClipboardCard(true);
            
            // Auto-hide clipboard card after 7 seconds
            if (focusTimer) clearTimeout(focusTimer);
            focusTimer = setTimeout(() => {
              setShowClipboardCard(false);
            }, 7000);
          }
        }
      } catch { /* ignore */ }
    };

    const handleFocus = () => {
      setTimeout(checkClipboard, 300);
    };

    window.addEventListener('focus', handleFocus);
    const apiCheckTimer = setTimeout(checkClipboard, 1000);

    return () => {
      window.removeEventListener('focus', handleFocus);
      clearTimeout(apiCheckTimer);
      if (focusTimer) clearTimeout(focusTimer);
    };
  }, []);

  const settingsRef = useRef({});
  useEffect(() => {
    settingsRef.current = {
      folder,
      downloadType,
      selectedAudioBitrate,
      selectedResolution,
      audioFormat,
      embedThumbnail,
      embedTags,
      embedChapters,
      customCoverFile,
      editedThumbnail,
      bandwidthLimit
    };
  }, [
    folder,
    downloadType,
    selectedAudioBitrate,
    selectedResolution,
    audioFormat,
    embedThumbnail,
    embedTags,
    embedChapters,
    customCoverFile,
    editedThumbnail,
    bandwidthLimit
  ]);

  /* ─── INIT ─── */
  const loadHistory = useCallback(async () => {
    try {
      const hist = await callApi('get_history');
      if (hist) setHistory(hist);
    } catch (e) { console.error('History load failed:', e); }
  }, []);

  const loadStorage = useCallback(async (dir) => {
    try {
      const targetDir = dir || '/';
      const data = await callApi('get_disk_usage', targetDir);
      if (data && !data.error) setStorage(data);
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    let retries = 0;
    let preloadTimer = null;
    let updateTimer = null;
    let retryTimer = null;

    const init = async () => {
      if (window.pywebview?.api && Object.keys(window.pywebview.api).length > 0) {
        try {
          const [lastFolder, depStatus] = await Promise.all([
            callApi('load_last_folder').catch(() => null),
            callApi('get_dependency_status').catch(e => {
              console.error('Failed to load dependency status:', e);
              return null;
            })
          ]);

          if (lastFolder) {
            setFolder(lastFolder);
            loadStorage(lastFolder);
          }

          // Preload history quietly after 2 seconds
          preloadTimer = setTimeout(() => {
            loadHistory();
          }, 2000);

          if (depStatus && !depStatus.error) {
            setDependencies(prev => ({
              ...prev,
              bemudex: depStatus.bemudex,
              ytdlp: { ...prev.ytdlp, version: depStatus.ytdlp.version },
              ffmpeg: {
                installed: depStatus.ffmpeg.installed,
                version: depStatus.ffmpeg.version,
                path: depStatus.ffmpeg.path
              },
              folderWritable: depStatus.folder_writable,
              status: depStatus.status
            }));
            setDependenciesLoaded(true);

            if (!startupCheckedRef.current) {
              if (depStatus.status === 'ready') {
                notifier.success('Ready to download');
              } else {
                notifier.warning('System health attention required');
              }
              startupCheckedRef.current = true;
            }

            // Background auto check if enabled (deferred by 1.5s to speed up UI render)
            const autoChk = localStorage.getItem('autoUpdateCheck');
            const shouldCheck = autoChk !== null ? JSON.parse(autoChk) : true;
            if (shouldCheck) {
              updateTimer = setTimeout(() => {
                callApi('check_ytdlp_updates').then(res => {
                  if (res && res.status === 'success') {
                    const now = new Date();
                    const lastCheckedStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' ' + (now.toLocaleDateString() === new Date().toLocaleDateString() ? 'Today' : now.toLocaleDateString());
                    setDependencies(prev => ({
                      ...prev,
                      ytdlp: {
                        ...prev.ytdlp,
                        version: res.installed,
                        latestVersion: res.latest,
                        updateAvailable: res.update_available,
                        status: res.update_available ? 'update_available' : 'up_to_date'
                      },
                      lastCheckedStr: lastCheckedStr
                    }));
                  }
                }).catch(() => {});
              }, 1500);
            }
          }
        } catch (e) { console.error('Init failed:', e); }
      } else if (retries < 30) {
        retries++;
        retryTimer = setTimeout(init, 100);
      }
    };
    init();
    window.addEventListener('pywebviewready', init);

    /* ─── CALLBACKS FROM PYTHON ─── */
    window.onMetadata = (data) => {
      setMetadataLoading(false);
      if (data.error) {
        setMetadataError(data.error);
        setMetadata(null);
        if (data.error.toLowerCase().includes('unsupported') || data.error.toLowerCase().includes('url')) {
          notifier.warning('Unsupported website. Please check the URL.');
        } else {
          notifier.error('Failed to fetch metadata. Please try again.');
        }
      } else {
        setMetadata(data);
        setMetadataError(null);
        if (data.resolutions?.length > 0) {
          setSelectedResolution(data.resolutions.includes(1080) ? '1080' : 'best');
        }
        setEditedTitle(data.title || '');
        setEditedArtist(data.channel || '');
        setEditedThumbnail(data.thumbnail || '');
        setCustomCoverFile(null);
        setIsEditingTitle(false);
        setIsEditingArtist(false);
      }
    };

    window.onProgress = (data) => {
      if (data.status === 'finished') {
        setQueue(prev => prev.filter(i => i.id !== data.id));
        setCompleted(prev => prev.some(i => i.id === data.id) ? prev : [...prev, data]);
        loadHistory();
      } else {
        if (data.status === 'failed') {
          notifier.error(data.sizeInfo || 'Download failed');
        }
        setQueue(prev => {
          const idx = prev.findIndex(i => i.id === data.id);
          if (idx > -1) {
            const nq = [...prev];
            nq[idx] = { ...nq[idx], ...data };
            return nq;
          }
          return [...prev, data];
        });
      }
    };

    window.onPlaylistMetadata = (items, isPlaylist) => {
      const {
        downloadType,
        selectedAudioBitrate,
        selectedResolution,
        folder,
        audioFormat,
        embedThumbnail,
        embedTags,
        embedChapters,
        customCoverFile,
        editedThumbnail,
        bandwidthLimit
      } = settingsRef.current;

      const params = lastDownloadParamsRef.current || {};
      const defaultQuality = downloadType === 'audio' ? selectedAudioBitrate : selectedResolution;
      const newItems = items.map(i => {
        const itemUrl = `https://www.youtube.com/watch?v=${i.id}`;
        return {
          id: i.id,
          title: i.title,
          percent: 0,
          speed: 'Queued',
          eta: 'Waiting',
          sizeInfo: 'Queued',
          status: 'queued',
          format: i.format,
          quality: i.quality,
          thumbnail: '',
          url: itemUrl,
          retryPayload: {
            url: itemUrl,
            folder: params.folder || folder,
            downloadType: params.downloadType || downloadType,
            quality: i.quality || params.quality || defaultQuality,
            options: {
              ...(params.options || {
                audioFormat,
                embedThumbnail,
                embedTags: downloadType === 'audio' ? embedTags : true,
                embedChapters: downloadType === 'audio' ? embedChapters : true,
                customCover: customCoverFile ? editedThumbnail : null,
                ratelimit: bandwidthLimit
              }),
              playlistIndex: i.index
            }
          }
        };
      });
      setQueue(prev => {
        const filtered = newItems.filter(ni => !prev.some(p => p.id === ni.id));
        return [...prev, ...filtered];
      });
      if (isPlaylist) {
        notifier.success('Playlist added to queue');
      }
    };

    window.onLog = (msg) => console.log('[Bemudex]:', msg);

    window.onDownloadFinished = (files, totalCount, wasCancelled) => {
      setDownloading(false);
      loadHistory();
      
      // Safety net: mark any leftover queued/downloading items as failed
      setQueue(prev => prev.map(item => {
        if (item.status === 'queued' || item.status === 'downloading') {
          return {
            ...item,
            status: 'failed',
            sizeInfo: wasCancelled ? 'Cancelled' : 'Failed to download'
          };
        }
        return item;
      }));

      if (wasCancelled) {
        notifier.info('Download cancelled');
        return;
      }

      if (files && files.length > 0) {
        const successCount = files.length;
        if (totalCount > 1) {
          if (successCount === totalCount) {
            notifier.success('Playlist completed');
          } else {
            notifier.warning(`Some playlist items failed (${successCount}/${totalCount} completed)`);
          }
        } else {
          notifier.success('Download completed');
        }
      } else if (totalCount > 0) {
        notifier.error('Download failed');
      }
    };

    return () => {
      window.removeEventListener('pywebviewready', init);
      window.onMetadata = null;
      window.onProgress = null;
      window.onPlaylistMetadata = null;
      window.onLog = null;
      window.onDownloadFinished = null;
      if (preloadTimer) clearTimeout(preloadTimer);
      if (updateTimer) clearTimeout(updateTimer);
      if (retryTimer) clearTimeout(retryTimer);
    };
  }, [loadHistory, loadStorage, notifier]);

  // Lazy-load history when history page becomes active
  useEffect(() => {
    let timer = null;
    if (activePage === 'history') {
      timer = setTimeout(() => {
        loadHistory();
      }, 0);
    }
    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [activePage, loadHistory]);

  /* ─── ACTIONS ─── */
  const fetchMetadata = (url) => {
    if (!url.trim()) return;
    setMetadataLoading(true);
    setMetadataError(null);
    setMetadata(null);
    callApi('fetch_metadata', url.trim()).catch(e => {
      setMetadataLoading(false);
      setMetadataError(String(e));
    });
  };

  /* ─── AUTO-FETCH ON PASTING/TYPING ─── */
  useEffect(() => {
    const trimmed = urlInput.trim();
    let timer = null;
    if (trimmed && trimmed !== lastFetchedUrlRef.current) {
      const isYouTubeUrl = trimmed.includes('youtube.com/') || trimmed.includes('youtu.be/');
      const isGeneralUrl = trimmed.startsWith('http://') || trimmed.startsWith('https://');
      
      if (isYouTubeUrl || isGeneralUrl) {
        lastFetchedUrlRef.current = trimmed;
        timer = setTimeout(() => {
          fetchMetadata(trimmed);
        }, 0);
      }
    } else if (!trimmed) {
      lastFetchedUrlRef.current = '';
      timer = setTimeout(() => {
        setMetadata(null);
        setMetadataError(null);
        setMetadataLoading(false);
        setEditedTitle('');
        setEditedArtist('');
        setEditedThumbnail('');
        setCustomCoverFile(null);
        setIsEditingTitle(false);
        setIsEditingArtist(false);
      }, 0);
    }
    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [urlInput]);

  const handleUrlSubmit = (e) => {
    if (e) e.preventDefault();
    fetchMetadata(urlInput);
  };

  const handlePaste = async () => {
    try {
      const text = await callApi('read_clipboard');
      if (text) { setUrlInput(text); fetchMetadata(text); }
    } catch (e) { console.error(e); }
  };

  const handleCoverArtSelect = (file) => {
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      showToast('Please select an image file.', 'error');
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      setEditedThumbnail(e.target.result);
      setCustomCoverFile(file);
      showToast('Cover art updated.', 'success');
    };
    reader.readAsDataURL(file);
  };

  const handleCoverArtChange = (e) => {
    const file = e.target.files?.[0];
    if (file) handleCoverArtSelect(file);
  };

  const handleCoverArtDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) handleCoverArtSelect(file);
  };

  const handleResizeStart = (e) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = panelWidth;

    const handleMouseMove = (moveEvent) => {
      const deltaX = moveEvent.clientX - startX;
      const newWidth = Math.max(260, Math.min(600, startWidth - deltaX));
      setPanelWidth(newWidth);
    };

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'default';
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'ew-resize';
  };

  const handleBrowse = async () => {
    try {
      const selected = await callApi('browse_folder');
      if (selected) { setFolder(selected); loadStorage(selected); }
    } catch (e) { console.error(e); }
  };

  const handleDownload = () => {
    if (!urlInput.trim() || !folder.trim()) return;

    const quality = downloadType === 'audio' ? selectedAudioBitrate : selectedResolution;
    const options = {
      audioFormat,
      title: downloadType === 'audio' ? editedTitle : null,
      artist: downloadType === 'audio' ? editedArtist : null,
      embedThumbnail,
      embedTags: downloadType === 'audio' ? embedTags : true,
      embedChapters: downloadType === 'audio' ? embedChapters : true,
      customCover: customCoverFile ? editedThumbnail : null, // Base64 string if custom cover is loaded
      ratelimit: bandwidthLimit // limit in MB/s
    };

    lastDownloadParamsRef.current = {
      folder: folder.trim(),
      downloadType,
      quality,
      options
    };

    const runActualDownload = () => {
      setDownloading(true);
      callApi('start_download', urlInput.trim(), folder.trim(), downloadType, quality, options)
        .catch(e => { console.error(e); setDownloading(false); });
    };

    const proceedWithDownload = () => {
      if (scheduleEnabled && scheduleTime) {
        const [sh, sm] = scheduleTime.split(':').map(Number);
        const now = new Date();
        const target = new Date();
        target.setHours(sh, sm, 0, 0);
        if (target <= now) {
          target.setDate(target.getDate() + 1);
        }
        const delayMs = target - now;
        const delayMin = Math.round(delayMs / 60000);
        
        notifier.info(`Download scheduled to run at ${scheduleTime} (in ${delayMin} min).`);
        
        const tempId = `sched_${Date.now()}`;
        setQueue([{
          id: tempId,
          title: editedTitle || metadata?.title || urlInput,
          format: downloadType,
          quality,
          percent: 0,
          status: 'queued',
          speed: `Scheduled for ${scheduleTime}`,
          eta: '',
          sizeInfo: ''
        }]);
        
        scheduledTimerRef.current = setTimeout(() => {
          setQueue([]);
          scheduledTimerRef.current = null;
          runActualDownload();
        }, delayMs);
      } else {
        runActualDownload();
      }
    };

    // Only run overwrite check for single downloads
    const isPlaylist = metadata?.is_playlist;
    if (!isPlaylist) {
      const checkTitle = editedTitle || metadata?.title || 'download';
      callApi('check_overwrite', folder.trim(), checkTitle, downloadType, audioFormat)
        .then(res => {
          if (res && res.exists) {
            showConfirm(
              `The file "${checkTitle}" already exists in the destination folder. Do you want to overwrite it?`,
              () => {
                proceedWithDownload();
              }
            );
          } else {
            proceedWithDownload();
          }
        })
        .catch(() => {
          proceedWithDownload();
        });
    } else {
      proceedWithDownload();
    }
  };

  const handleCancel = useCallback(() => {
    if (scheduledTimerRef.current) {
      clearTimeout(scheduledTimerRef.current);
      scheduledTimerRef.current = null;
    }
    callApi('cancel_download').then(() => {
      setQueue([]);
      setDownloading(false);
    }).catch(console.error);
  }, []);

  const handleRetryDownload = useCallback((item) => {
    if (downloading) {
      notifier.warning('Finish current download before retrying.');
      return;
    }
    if (!item.retryPayload) {
      notifier.error('Cannot retry: download parameters missing.');
      return;
    }
    const { url, folder, downloadType, quality, options } = item.retryPayload;
    
    // Set this item to queued state in UI
    setQueue(prev => prev.map(i => {
      if (i.id === item.id) {
        return {
          ...i,
          status: 'queued',
          percent: 0,
          speed: 'Queued',
          eta: 'Waiting',
          sizeInfo: 'Queued'
        };
      }
      return i;
    }));
    
    setDownloading(true);
    callApi('start_download', url, folder, downloadType, quality, options)
      .catch(e => {
        console.error(e);
        setDownloading(false);
        setQueue(prev => prev.map(i => {
          if (i.id === item.id) {
            return {
              ...i,
              status: 'failed',
              sizeInfo: String(e)
            };
          }
          return i;
        }));
      });
  }, [notifier, downloading]);

  const handleCancelItem = useCallback((item) => {
    if (item.status === 'failed') {
      // Just filter it out of the queue list
      setQueue(prev => prev.filter(i => i.id !== item.id));
    } else {
      // For active/queued downloads, trigger standard cancellation
      handleCancel();
    }
  }, [handleCancel]);

  const handlePlayFile = useCallback((fp) => {
    callApi('play_file', fp)
      .then(ok => {
        if (!ok) notifier.error('File no longer exists or has been moved.');
      })
      .catch(err => {
        console.error(err);
        notifier.error('Failed to open file.');
      });
  }, [notifier]);

  const handleOpenFolder = useCallback((fp) => {
    callApi('open_folder', fp)
      .then(ok => {
        if (!ok) notifier.error('Folder no longer exists or has been moved.');
      })
      .catch(err => {
        console.error(err);
        notifier.error('Failed to open folder.');
      });
  }, [notifier]);

  const handleClearAll = useCallback(() => {
    if (downloading) {
      setQueue(prev => prev.filter(i => 
        i.status === 'downloading' || 
        i.status === 'queued' || 
        i.status === 'converting'
      ));
      setCompleted([]);
    } else {
      setQueue([]);
      setCompleted([]);
    }
  }, [downloading]);

  const handleDeleteHistory = useCallback(async (fp) => {
    const ok = await callApi('remove_history_item', fp);
    if (ok) {
      setHistory(prev => prev.filter(i => i.filePath !== fp));
      notifier.success('Item removed from history.');
    }
  }, [notifier]);

  const handleClearHistory = useCallback(() => {
    showConfirm('Delete all download history permanently? This cannot be undone.', async () => {
      await callApi('clear_history');
      setHistory([]);
      showToast('History cleared.', 'success');
    });
  }, [showConfirm, showToast]);
  const handleCheckYtdlpUpdates = async (silent = false) => {
    if (!silent) {
      setDependencies(prev => ({ ...prev, ytdlp: { ...prev.ytdlp, status: 'checking', checking: true } }));
    }
    try {
      const res = await callApi('check_ytdlp_updates');
      if (res && res.status === 'success') {
        const now = new Date();
        const lastCheckedStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' ' + (now.toLocaleDateString() === new Date().toLocaleDateString() ? 'Today' : now.toLocaleDateString());
        
        setDependencies(prev => ({
          ...prev,
          ytdlp: {
            ...prev.ytdlp,
            version: res.installed,
            latestVersion: res.latest,
            updateAvailable: res.update_available,
            status: res.update_available ? 'update_available' : 'up_to_date',
            checking: false
          },
          lastCheckedStr: lastCheckedStr
        }));
        
        if (res.update_available && !silent) {
          showToast('Engine update is available!', 'info');
        } else if (!res.update_available && !silent) {
          showToast('yt-dlp is up to date.', 'success');
        }
      } else {
        setDependencies(prev => ({ ...prev, ytdlp: { ...prev.ytdlp, status: 'unknown', checking: false } }));
        if (!silent) {
          showToast(res.message || 'Unable to check for updates.', 'error');
        }
      }
    } catch {
      setDependencies(prev => ({ ...prev, ytdlp: { ...prev.ytdlp, status: 'unknown', checking: false } }));
      if (!silent) {
        showToast('Unable to check for updates.', 'error');
      }
    }
  };

  const handleUpdateEngine = async () => {
    setDependencies(prev => ({ ...prev, ytdlp: { ...prev.ytdlp, status: 'updating', updating: true } }));
    try {
      const res = await callApi('update_ytdlp');
      if (res.status === 'success') {
        showToast(res.message || 'yt-dlp engine updated successfully. Please restart Bemudex to apply the update.', 'success', 8000);
        
        const depStatus = await callApi('get_dependency_status');
        if (depStatus && !depStatus.error) {
          setDependencies(prev => ({
            ...prev,
            ytdlp: {
              ...prev.ytdlp,
              version: depStatus.ytdlp.version,
              latestVersion: depStatus.ytdlp.version,
              updateAvailable: false,
              status: 'up_to_date',
              updating: false
            },
            ffmpeg: {
              installed: depStatus.ffmpeg.installed,
              version: depStatus.ffmpeg.version,
              path: depStatus.ffmpeg.path
            },
            folderWritable: depStatus.folder_writable,
            status: depStatus.status
          }));
        } else {
          setDependencies(prev => ({ ...prev, ytdlp: { ...prev.ytdlp, updating: false, status: 'up_to_date', updateAvailable: false } }));
        }
      } else {
        showToast(`Update failed: ${res.message}`, 'error', 6000);
        setDependencies(prev => ({ ...prev, ytdlp: { ...prev.ytdlp, status: 'update_available', updating: false } }));
      }
    } catch (e) {
      showToast(`Update failed: ${e}`, 'error', 6000);
      setDependencies(prev => ({ ...prev, ytdlp: { ...prev.ytdlp, status: 'update_available', updating: false } }));
    }
  };

  const handleLocateFfmpeg = async () => {
    try {
      const res = await callApi('locate_ffmpeg');
      if (res.status === 'success') {
        showToast('✓ FFmpeg detected', 'success');
        
        const depStatus = await callApi('get_dependency_status');
        if (depStatus && !depStatus.error) {
          setDependencies(prev => ({
            ...prev,
            ffmpeg: {
              installed: depStatus.ffmpeg.installed,
              version: depStatus.ffmpeg.version,
              path: depStatus.ffmpeg.path
            },
            folderWritable: depStatus.folder_writable,
            status: depStatus.status
          }));
        }
      } else if (res.status === 'error') {
        showToast(`⚠ Failed to detect FFmpeg: ${res.message}`, 'error');
      }
    } catch {
      showToast('⚠ Failed to detect FFmpeg', 'error');
    }
  };

  const handleRetryFfmpegDetection = async () => {
    setDependencies(prev => ({ ...prev, ffmpeg: { ...prev.ffmpeg, checking: true } }));
    try {
      const res = await callApi('detect_ffmpeg_api');
      if (res.installed) {
        showToast('✓ FFmpeg detected', 'success');
      } else {
        showToast('⚠ FFmpeg not found', 'warning');
      }
      
      const depStatus = await callApi('get_dependency_status');
      if (depStatus && !depStatus.error) {
        setDependencies(prev => ({
          ...prev,
          ffmpeg: {
            installed: depStatus.ffmpeg.installed,
            version: depStatus.ffmpeg.version,
            path: depStatus.ffmpeg.path
          },
          folderWritable: depStatus.folder_writable,
          status: depStatus.status
        }));
      }
    } catch {
      showToast('⚠ FFmpeg detection failed', 'error');
    } finally {
      setDependencies(prev => ({ ...prev, ffmpeg: { ...prev.ffmpeg, checking: false } }));
    }
  };

  const handleInstallFfmpeg = () => {
    showToast('Auto-installing FFmpeg is coming soon. Please download and locate FFmpeg manually.', 'info');
  };

  const handleResetDependencyConfig = () => {
    showConfirm('Reset dependency configuration? This will clear custom paths and re-run system detection.', async () => {
      try {
        const res = await callApi('reset_dependency_config');
        if (res && !res.error) {
          setDependencies(prev => ({
            ...prev,
            bemudex: res.bemudex,
            ytdlp: {
              ...prev.ytdlp,
              version: res.ytdlp.version,
              latestVersion: '',
              updateAvailable: false,
              status: 'unknown'
            },
            ffmpeg: {
              installed: res.ffmpeg.installed,
              version: res.ffmpeg.version,
              path: res.ffmpeg.path
            },
            folderWritable: res.folder_writable,
            status: res.status
          }));
          showToast('Dependency configuration reset successfully.', 'success');
        }
      } catch {
        showToast('Failed to reset configuration.', 'error');
      }
    });
  };

  const handleViewDiagnostics = async () => {
    setLoadingDiagnostics(true);
    try {
      const res = await callApi('get_diagnostics', darkMode ? 'dark' : 'light');
      if (res && !res.error) {
        setDiagnostics(res);
        setShowDiagnosticsModal(true);
        notifier.success('Diagnostics completed');
      } else {
        notifier.error('Failed to generate diagnostics.');
      }
    } catch {
      notifier.error('Failed to generate diagnostics.');
    } finally {
      setLoadingDiagnostics(false);
    }
  };

  const handleCopyDiagnostics = () => {
    if (!diagnostics) return;
    const txt = `### Bemudex Diagnostics Report
- **Bemudex Version**: ${diagnostics.bemudex_version}
- **Build Number**: ${diagnostics.build_number}
- **Release Channel**: ${diagnostics.release_channel}
- **Operating System**: ${diagnostics.os} (${diagnostics.os_release})
- **Architecture**: ${diagnostics.architecture}
- **Python Version**: ${diagnostics.python_version}
- **Download Folder**: ${diagnostics.downloads_folder}
- **Download Folder Writable**: ${diagnostics.folder_writable ? "Yes" : "No (" + diagnostics.folder_writable_status + ")"}
- **yt-dlp Version**: ${diagnostics.ytdlp_version}
- **FFmpeg Version**: ${diagnostics.ffmpeg_version}
- **FFmpeg Path**: ${diagnostics.ffmpeg_path}
- **Config File Location**: ${diagnostics.config_file_location}
- **Current Theme**: ${diagnostics.current_theme}
- **Backend Status**: ${diagnostics.backend_status}
- **Internet Reachability**: ${diagnostics.internet_status}`;

    callApi('copy_to_clipboard', txt)
      .then(ok => {
        if (ok) showToast('Diagnostics copied to clipboard!', 'success');
        else showToast('Failed to copy to clipboard.', 'error');
      })
      .catch(() => showToast('Failed to copy to clipboard.', 'error'));
  };

  const activeCount = queue.length;
  const showPanel = activeCount > 0 || completed.length > 0;

  const filteredHistory = useMemo(() => {
    return history.filter(item => {
      const matchesSearch = !debouncedSearch || item.title?.toLowerCase().includes(debouncedSearch.toLowerCase());
      const matchesFilter = historyFilter === 'all' || item.format === historyFilter;
      return matchesSearch && matchesFilter;
    });
  }, [history, debouncedSearch, historyFilter]);

  /* ─── AVAILABLE RESOLUTIONS ─── */
  const availableResolutions = useMemo(() => {
    return metadata?.resolutions || [2160, 1440, 1080, 720, 480];
  }, [metadata]);

  /* ─────────────────────── RENDER ─────────────────────── */
  return (
    <div
      className={`app-shell ${showPanel ? 'has-panel' : ''} ${collapsed ? 'sidebar-collapsed' : ''} ${darkMode ? '' : 'theme-light'}`}
      style={{ '--panel-width': `${panelWidth}px` }}
    >

      {/* ═══ CLIPBOARD PASTE CARD ═══ */}
      {showClipboardCard && (
        <div className="clipboard-card-wrap">
          <div className="clipboard-card">
            <div className="clipboard-icon"><Link size={15} /></div>
            <div className="clipboard-content">
              <span className="clipboard-title">Link detected in clipboard</span>
              <span className="clipboard-desc">Click Fetch to analyze this URL.</span>
            </div>
            <button
              className="clipboard-btn-action"
              onClick={() => {
                setUrlInput(clipboardUrl);
                setShowClipboardCard(false);
              }}
            >
              Fetch
            </button>
            <button
              className="clipboard-btn-close"
              onClick={() => setShowClipboardCard(false)}
              aria-label="Dismiss clipboard prompt"
            >
              <X size={12} />
            </button>
          </div>
        </div>
      )}

      {/* ═══ TOAST NOTIFICATIONS ═══ */}
      <div className="toast-container" aria-live="polite" aria-atomic="false">
        {toasts.map(t => (
          <div key={t.id} className={`toast toast-${t.type}`} role="status">
            {t.type === 'success' && <CheckCircle2 size={14} aria-hidden="true" />}
            {t.type === 'error'   && <AlertTriangle size={14} aria-hidden="true" />}
            {t.type === 'info'    && <Info size={14} aria-hidden="true" />}
            <span>{t.message}</span>
            <button className="toast-close" onClick={() => setToasts(p => p.filter(x => x.id !== t.id))} aria-label="Dismiss notification"><X size={12} /></button>
          </div>
        ))}
      </div>

      {/* ═══ CONFIRM DIALOG ═══ */}
      {confirmDialog && (
        <div className="confirm-overlay" role="dialog" aria-modal="true" aria-label="Confirm action">
          <div className="confirm-box">
            <div className="confirm-icon"><AlertTriangle size={20} /></div>
            <p className="confirm-message">{confirmDialog.message}</p>
            <div className="confirm-actions">
              <button className="confirm-btn confirm-cancel" onClick={() => setConfirmDialog(null)}>Cancel</button>
              <button className="confirm-btn confirm-ok" onClick={() => { confirmDialog.onConfirm(); setConfirmDialog(null); }}>Confirm</button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ DIAGNOSTICS MODAL ═══ */}
      {showDiagnosticsModal && diagnostics && (
        <div className="confirm-overlay" role="dialog" aria-modal="true" aria-label="System diagnostics">
          <div className="confirm-box diagnostics-modal">
            <div className="diagnostics-modal-header">
              <span className="diagnostics-modal-title">System Diagnostics</span>
              <button className="diagnostics-close" onClick={() => setShowDiagnosticsModal(false)} aria-label="Close modal"><X size={15} /></button>
            </div>
            <div className="diagnostics-modal-body">
              <div className="diagnostics-code-box">
                <pre>
{`### Bemudex Diagnostics Report
- **Bemudex Version**: ${diagnostics.bemudex_version}
- **Build Number**: ${diagnostics.build_number}
- **Release Channel**: ${diagnostics.release_channel}
- **Operating System**: ${diagnostics.os} (${diagnostics.os_release})
- **Architecture**: ${diagnostics.architecture}
- **Python Version**: ${diagnostics.python_version}
- **Download Folder**: ${diagnostics.downloads_folder}
- **Download Folder Writable**: ${diagnostics.folder_writable ? "Yes" : "No (" + diagnostics.folder_writable_status + ")"}
- **yt-dlp Version**: ${diagnostics.ytdlp_version}
- **FFmpeg Version**: ${diagnostics.ffmpeg_version}
- **FFmpeg Path**: ${diagnostics.ffmpeg_path}
- **Config File Location**: ${diagnostics.config_file_location}
- **Current Theme**: ${diagnostics.current_theme}
- **Backend Status**: ${diagnostics.backend_status}
- **Internet Reachability**: ${diagnostics.internet_status}`}
                </pre>
              </div>
            </div>
            <div className="confirm-actions diagnostics-actions">
              <button className="confirm-btn confirm-cancel" onClick={() => setShowDiagnosticsModal(false)}>Close</button>
              <button className="confirm-btn confirm-ok" onClick={handleCopyDiagnostics}>Copy Diagnostics</button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ SIDEBAR ═══ */}
      <aside className="sidebar">
        <div>
          <div className="sidebar-header">
            <div className="sidebar-header-left">
              <img src="/bemudex_32.png" className="sidebar-logo" alt="Bemudex Logo" />
              {!collapsed && (
                <div className="sidebar-brand-text">
                  <span className="sidebar-app-name">Bemudex</span>
                </div>
              )}
            </div>
            <button className="sidebar-toggle-btn" onClick={() => setCollapsed(!collapsed)} title={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
              {collapsed ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}
            </button>
          </div>

          <nav className="sidebar-nav">
            <button className={`nav-item ${activePage === 'home' ? 'active' : ''}`} onClick={() => setActivePage('home')} title={collapsed ? "Home" : ""}>
              <Home size={16} /> {!collapsed && <span>Home</span>}
            </button>
            <button className={`nav-item ${activePage === 'history' ? 'active' : ''}`} onClick={() => setActivePage('history')} title={collapsed ? "History" : ""}>
              <HistoryIcon size={16} /> 
              {!collapsed && <span>History</span>}
              {!collapsed && history.length > 0 && <span className="nav-badge">{history.length}</span>}
            </button>
            <button className={`nav-item ${activePage === 'settings' ? 'active' : ''}`} onClick={() => setActivePage('settings')} title={collapsed ? "Settings" : ""}>
              <SettingsIcon size={16} /> {!collapsed && <span>Settings</span>}
            </button>

            {!collapsed && <div className="nav-section-label">Coming Soon</div>}
            <div className="nav-item nav-item-disabled" aria-disabled="true" title={collapsed ? "Playlists (Coming Soon)" : "Coming Soon"} role="presentation">
              <ListMusic size={16} aria-hidden="true" /> {!collapsed && <span>Playlists</span>}
            </div>

            {/* Tip Card */}
            {!collapsed && showTip && (
              <div className="tip-card" style={{ marginTop: 20 }}>
                <div className="tip-card-header"><Zap size={13} /> Tip of the Day</div>
                <div className="tip-card-body">
                  You can paste a YouTube playlist or channel URL to download multiple videos at once.
                </div>
                <button className="tip-card-dismiss" onClick={() => { setShowTip(false); localStorage.setItem('hideTip', 'true'); }}>Got it</button>
              </div>
            )}
          </nav>
        </div>

        <div className="sidebar-footer">
          {!collapsed ? (
            <>
              {/* Storage */}
              {storage && (
                <div className="storage-section">
                  <span className="storage-label"><HardDrive size={12} /> Storage</span>
                  <div className="storage-bar-track">
                    <div className="storage-bar-fill" style={{ width: `${((storage.used || 0) / (storage.total || 1)) * 100}%` }} />
                  </div>
                  <span className="storage-info">{storage.free_str} free of {storage.total_str}</span>
                </div>
              )}

              <div className="engine-info">
                <span className="engine-version">Engine <span>v{dependencies.ytdlp.version}</span></span>
                <span className="engine-status">
                  <span className={`engine-dot ${dependencies.ytdlp.updateAvailable ? 'warning' : 'healthy'}`} />
                  {dependencies.ytdlp.updateAvailable ? 'Update Available' : 'Up to date'}
                </span>
              </div>

              <button className="btn-update-engine" onClick={() => handleCheckYtdlpUpdates()} disabled={dependencies.ytdlp.checking || dependencies.ytdlp.updating || downloading}>
                <RefreshCw size={12} className={dependencies.ytdlp.checking || dependencies.ytdlp.updating ? 'spinner' : ''} />
                {dependencies.ytdlp.updating ? 'Updating...' : dependencies.ytdlp.checking ? 'Checking...' : 'Check for Updates'}
              </button>
            </>
          ) : (
            storage && (
              <div className="storage-section collapsed" title={`Storage: ${storage.free_str} free of ${storage.total_str}`}>
                <HardDrive size={16} style={{ color: 'var(--text-muted)', margin: '0 auto', display: 'block' }} />
              </div>
            )
          )}
        </div>
      </aside>

      {/* ═══ MAIN CONTENT ═══ */}
      <main className="main-content">
        {/* ──── PERSISTENT HEALTH BANNERS ──── */}
        {dependenciesLoaded && (
          <div className="persistent-banners-container">
            {!dependencies.ffmpeg.installed && (
              <div className="alert-banner error" role="alert">
                <AlertTriangle size={15} />
                <div><strong>FFmpeg missing:</strong> FFmpeg is required for conversion. Please locate or install FFmpeg under Settings.</div>
              </div>
            )}

            {!dependencies.folderWritable && (
              <div className="alert-banner error" role="alert">
                <AlertTriangle size={15} />
                <div><strong>Download folder not writable:</strong> The selected folder does not have write permissions or is missing. Please select another folder.</div>
              </div>
            )}

            {dependencies.ytdlp.updateAvailable && (
              <div className="alert-banner warning" role="alert">
                <AlertCircle size={15} />
                <div style={{ flex: 1 }}><strong>yt-dlp engine outdated:</strong> A new version of yt-dlp is available (Latest: {dependencies.ytdlp.latestVersion}).</div>
                <button 
                  className="settings-btn primary" 
                  style={{ padding: '4px 8px', fontSize: '11px', minHeight: 'auto', marginLeft: '12px' }}
                  onClick={handleUpdateEngine}
                  disabled={dependencies.ytdlp.updating}
                >
                  {dependencies.ytdlp.updating ? 'Updating...' : 'Update Now'}
                </button>
              </div>
            )}
          </div>
        )}

        {/* ──── HOME PAGE ──── */}
        {activePage === 'home' && (
          <div className="animate-fade-in" key="home">
            <div className="page-header">
              <h1 className="page-title">{getGreeting()}</h1>
              <p className="page-subtitle">Drop a YouTube link to begin your next download.</p>
            </div>

            {/* URL Input */}
            <div className="url-input-hero">
              <form onSubmit={handleUrlSubmit}>
                <div className="url-input-wrapper">
                  <Link size={16} className="url-icon" />
                  <input
                    className="url-input-field"
                    type="text"
                    placeholder="https://www.youtube.com/watch?v=..."
                    value={urlInput}
                    onChange={(e) => setUrlInput(e.target.value)}
                    disabled={downloading}
                    aria-label="Video URL"
                  />
                  {urlInput && (
                    <button type="button" className="url-clear-btn" onClick={() => { setUrlInput(''); setMetadata(null); setMetadataError(null); }}>
                      <X size={14} />
                    </button>
                  )}
                  {urlInput.trim() ? (
                    <button type="submit" className="url-paste-btn" disabled={metadataLoading || downloading}>
                      {metadataLoading ? <RefreshCw size={13} className="spinner" /> : <Search size={13} />}
                      {metadataLoading ? 'Fetching...' : 'Fetch'}
                    </button>
                  ) : (
                    <button type="button" className="url-paste-btn" onClick={handlePaste} disabled={downloading}>
                      <Clipboard size={13} /> Paste
                    </button>
                  )}
                </div>
              </form>
              <div className="url-hint">
                <span>Press</span> <kbd className="kbd">Enter</kbd> <span>or click Fetch to analyze the link</span>
              </div>
            </div>

            {/* Metadata Skeleton */}
            {metadataLoading && (() => {
              const isPlaylist = urlInput.includes('list=') || urlInput.includes('playlist');
              const entryCount = null; // Stays null as backend is synchronous

              return (
                <div className="metadata-preview">
                  <div className="metadata-skeleton">
                    <div className="skeleton-thumb"><div className="skeleton skeleton-thumbnail" /></div>
                    <div className="skeleton-info">
                      <div className="skeleton skeleton-text-lg" style={{ width: '80%' }} />
                      <div className="skeleton skeleton-text" style={{ width: '50%' }} />
                      <div className="skeleton skeleton-text" style={{ width: '35%' }} />
                      <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                        <div className="skeleton" style={{ width: 42, height: 22, borderRadius: 4 }} />
                        <div className="skeleton" style={{ width: 52, height: 22, borderRadius: 4 }} />
                        <div className="skeleton" style={{ width: 38, height: 22, borderRadius: 4 }} />
                      </div>
                    </div>
                  </div>
                  
                  {isPlaylist && (
                    <div className="metadata-loading-info animate-fade-in">
                      {entryCount !== null ? (
                        <>
                          <div className="loading-accent">
                            <RefreshCw size={13} className="spinner" />
                            <span>Playlist detected: <strong>{entryCount} tracks</strong></span>
                          </div>
                          <p style={{ margin: '4px 0 2px 0' }}>Analyzing playlist metadata...</p>
                          <p className="loading-subtext">
                            Large playlists may take up to a minute depending on playlist size and YouTube response times.
                          </p>
                          <p className="loading-subtext" style={{ marginTop: 4, fontWeight: 500 }}>Please wait.</p>
                        </>
                      ) : (
                        <>
                          <div className="loading-accent">
                            <RefreshCw size={13} className="spinner" />
                            <span>Analyzing playlist metadata...</span>
                          </div>
                          <p className="loading-subtext" style={{ marginTop: 4 }}>
                            Large playlists may take some time to process.
                          </p>
                          <p className="loading-subtext" style={{ marginTop: 4, fontWeight: 500 }}>Please wait.</p>
                        </>
                      )}
                    </div>
                  )}
                </div>
              );
            })()}

            {/* Metadata Error */}
            {metadataError && (
              <div className="alert-banner" style={{ marginBottom: 20 }}>
                <AlertTriangle size={16} />
                <div>Could not fetch metadata. Check the URL and try again.</div>
              </div>
            )}

            {/* Metadata Preview */}
            {metadata && !metadataLoading && (
              <div className="metadata-preview">
                <div className="metadata-content">
                  <div 
                    className="metadata-thumbnail-wrap editable"
                    onClick={() => document.getElementById('cover-art-file-input').click()}
                    onDragOver={e => e.preventDefault()}
                    onDrop={handleCoverArtDrop}
                    title="Drag & Drop image or click to change cover art"
                  >
                    <img className="metadata-thumbnail" src={editedThumbnail || metadata.thumbnail} alt="" loading="eager" />
                    <div className="metadata-thumbnail-overlay">
                      <Plus size={16} />
                      <span>Change Cover</span>
                    </div>
                    {metadata.duration_str && <span className="metadata-duration-badge">{metadata.duration_str}</span>}
                    <input 
                      type="file" 
                      id="cover-art-file-input" 
                      accept="image/*" 
                      style={{ display: 'none' }} 
                      onChange={handleCoverArtChange} 
                    />
                  </div>
                  <div className="metadata-info">
                    {isEditingTitle ? (
                      <input 
                        type="text" 
                        className="metadata-edit-input title-edit" 
                        value={editedTitle} 
                        onChange={e => setEditedTitle(e.target.value)}
                        onBlur={() => setIsEditingTitle(false)}
                        onKeyDown={e => { if (e.key === 'Enter') setIsEditingTitle(false); }}
                        autoFocus
                        placeholder="Video title..."
                      />
                    ) : (
                      <h2 className="metadata-title editable" onClick={() => setIsEditingTitle(true)} title="Click to edit title">
                        {editedTitle || metadata.title}
                        <Edit3 size={11} className="edit-pencil-icon" />
                      </h2>
                    )}

                    {isEditingArtist ? (
                      <input 
                        type="text" 
                        className="metadata-edit-input artist-edit" 
                        value={editedArtist} 
                        onChange={e => setEditedArtist(e.target.value)}
                        onBlur={() => setIsEditingArtist(false)}
                        onKeyDown={e => { if (e.key === 'Enter') setIsEditingArtist(false); }}
                        autoFocus
                        placeholder="Artist or Channel name..."
                      />
                    ) : (
                      <div className="metadata-channel editable" onClick={() => setIsEditingArtist(true)} title="Click to edit artist">
                        {editedArtist || metadata.channel}
                        <Edit3 size={11} className="edit-pencil-icon" />
                      </div>
                    )}

                    <div className="metadata-stats">
                      {formatViews(metadata.view_count)}
                      {metadata.upload_date ? ` • ${metadata.upload_date}` : ''}
                    </div>
                    <div className="metadata-format-badges">
                      {metadata.resolutions?.includes(4320) && <span className="format-badge highlight">8K</span>}
                      {metadata.resolutions?.includes(2160) && !metadata.resolutions?.includes(4320) && <span className="format-badge highlight">4K</span>}
                      {metadata.resolutions?.includes(1440) && !metadata.resolutions?.includes(2160) && !metadata.resolutions?.includes(4320) && <span className="format-badge">1440p</span>}
                      {metadata.resolutions?.includes(1080) && !metadata.resolutions?.includes(1440) && !metadata.resolutions?.includes(2160) && !metadata.resolutions?.includes(4320) && <span className="format-badge">1080p</span>}
                      {metadata.fps >= 60 && <span className="format-badge">{metadata.fps}fps</span>}
                      {metadata.has_hdr && <span className="format-badge highlight">HDR</span>}
                      {metadata.has_av1 && <span className="format-badge highlight">AV1</span>}
                      {metadata.has_vp9 && <span className="format-badge">VP9</span>}
                      {(metadata.resolutions?.length > 0) && <span className="format-badge"><MonitorPlay size={11} style={{ marginRight: 2 }} /> MP4</span>}
                      <span className="format-badge"><Headphones size={11} style={{ marginRight: 2 }} /> MP3</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Format Workspace — shown after metadata or always */}
            {(metadata || !metadataLoading) && !metadataError && (
              <div className="format-section">
                {/* Video / Audio Tabs */}
                <div className="format-tabs">
                  <button className={`format-tab ${downloadType === 'video' ? 'active' : ''}`} onClick={() => setDownloadType('video')}>
                    <Video size={15} /> Video
                  </button>
                  <button className={`format-tab ${downloadType === 'audio' ? 'active' : ''}`} onClick={() => setDownloadType('audio')}>
                    <Music size={15} /> Audio
                  </button>
                </div>

                {/* Video Workspace */}
                {downloadType === 'video' && (
                  <div className="workspace-content" key="video">
                    <div className="workspace-group">
                      <span className="workspace-label">Quality</span>
                      <div className="quality-cards">
                        <div className={`quality-card ${selectedResolution === 'best' ? 'active' : ''}`} onClick={() => setSelectedResolution('best')}>
                          <span className="quality-card-check"><Check size={12} /></span>
                          <span className="quality-card-value">Best</span>
                          <span className="quality-card-label">Available</span>
                          {metadata?.resolution_sizes?.['best'] && <span className="quality-card-size">{metadata.resolution_sizes['best']}</span>}
                        </div>
                        {availableResolutions.filter(h => h >= 480).map(h => {
                          const estSize = metadata?.resolution_sizes?.[String(h)];
                          return (
                            <div
                              key={h}
                              className={`quality-card ${selectedResolution === String(h) ? 'active' : ''}`}
                              onClick={() => setSelectedResolution(String(h))}
                            >
                              <span className="quality-card-check"><Check size={12} /></span>
                              {h === 1080 && <span className="quality-popular-badge">Popular</span>}
                              <span className="quality-card-value">{resolutionLabel(h)}</span>
                              <span className="quality-card-label">{resolutionSublabel(h)}</span>
                              {estSize && <span className="quality-card-size">{estSize}</span>}
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Save Location */}
                    <div className="workspace-group">
                      <span className="workspace-label">Save to</span>
                      <div className="save-location">
                        <FolderOpen size={15} className="save-location-icon" aria-hidden="true" />
                        <span className={`save-location-path ${!folder ? 'empty' : ''}`}>
                          {folder || 'Select a destination folder...'}
                        </span>
                        <button className="btn-browse" onClick={handleBrowse}>Browse</button>
                      </div>
                    </div>
                  </div>
                )}

                {/* Audio Workspace */}
                {downloadType === 'audio' && (
                  <div className="workspace-content audio-workspace-split" key="audio">
                    {/* Left Column: Artwork & Tag Editor */}
                    <div className="audio-meta-column">
                      <div className="audio-cover-wrapper">
                        {(editedThumbnail || metadata?.thumbnail) ? (
                          <img className="audio-cover-art" src={editedThumbnail || metadata?.thumbnail} alt="Cover Art" />
                        ) : (
                          <div className="audio-cover-placeholder">
                            <Music size={32} />
                          </div>
                        )}
                        <span className="audio-cover-badge">TAGGER</span>
                      </div>
                      <div className="audio-tag-inputs">
                        <div className="tag-input-group">
                          <label className="tag-label">Track Title</label>
                          <input 
                            type="text" 
                            className="tag-input" 
                            value={editedTitle} 
                            onChange={e => setEditedTitle(e.target.value)} 
                            placeholder="Song title..."
                            disabled={!metadata}
                          />
                        </div>
                        <div className="tag-input-group">
                          <label className="tag-label">Artist / Channel</label>
                          <input 
                            type="text" 
                            className="tag-input" 
                            value={editedArtist} 
                            onChange={e => setEditedArtist(e.target.value)} 
                            placeholder="Artist name..."
                            disabled={!metadata}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Right Column: Audio Output Settings */}
                    <div className="audio-settings-column">
                      {/* 1. Format Selection */}
                      <div className="workspace-group">
                        <span className="workspace-label">Audio Format</span>
                        <div className="quality-cards">
                          {[
                            { key: 'mp3', label: 'MP3', sub: 'MPEG Layer 3', popular: true },
                            { key: 'flac', label: 'FLAC', sub: 'Lossless Audio' },
                            { key: 'm4a', label: 'AAC', sub: 'Apple Audio (M4A)' },
                            { key: 'wav', label: 'WAV', sub: 'Uncompressed PCM' }
                          ].map(opt => (
                            <div
                              key={opt.key}
                              className={`quality-card ${audioFormat === opt.key ? 'active' : ''}`}
                              onClick={() => setAudioFormat(opt.key)}
                            >
                              <span className="quality-card-check"><Check size={12} /></span>
                              {opt.popular && <span className="quality-popular-badge">HQ</span>}
                              <span className="quality-card-value">{opt.label}</span>
                              <span className="quality-card-label">{opt.sub}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* 2. Bitrate (only for lossy MP3 / AAC) */}
                      {(audioFormat === 'mp3' || audioFormat === 'm4a') && (
                        <div className="workspace-group animate-fade-in" style={{ marginTop: 4 }}>
                          <span className="workspace-label">Target Bitrate</span>
                          <div className="quality-cards">
                            {[
                              { key: '320', label: '320 kbps', sub: 'Insane Quality', popular: true },
                              { key: '256', label: '256 kbps', sub: 'Very High' },
                              { key: '192', label: '192 kbps', sub: 'High Quality' },
                              { key: '128', label: '128 kbps', sub: 'Standard' }
                            ].map(opt => (
                              <div
                                key={opt.key}
                                className={`quality-card ${selectedAudioBitrate === opt.key ? 'active' : ''}`}
                                onClick={() => setSelectedAudioBitrate(opt.key)}
                              >
                                <span className="quality-card-check"><Check size={12} /></span>
                                {opt.popular && <span className="quality-popular-badge">Best</span>}
                                <span className="quality-card-value">{opt.label}</span>
                                <span className="quality-card-label">{opt.sub}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* 3. Toggles */}
                      <div className="workspace-group">
                        <span className="workspace-label">Embedding Options</span>
                        <div className="audio-toggles-container">
                          <div className="audio-toggle-row">
                            <span className="audio-toggle-label">Embed Artwork Thumbnail</span>
                            <label className="toggle small">
                              <input type="checkbox" checked={embedThumbnail} onChange={e => setEmbedThumbnail(e.target.checked)} />
                              <span className="toggle-track" />
                            </label>
                          </div>
                          <div className="audio-toggle-row">
                            <span className="audio-toggle-label">Write ID3 Metadata Tags</span>
                            <label className="toggle small">
                              <input type="checkbox" checked={embedTags} onChange={e => setEmbedTags(e.target.checked)} />
                              <span className="toggle-track" />
                            </label>
                          </div>
                          <div className="audio-toggle-row" style={{ opacity: metadata?.has_chapters ? 1 : 0.5 }}>
                            <span className="audio-toggle-label">
                              Embed Audio Chapters {metadata?.has_chapters ? '✓' : '(Not detected)'}
                            </span>
                            <label className="toggle small">
                              <input 
                                type="checkbox" 
                                checked={embedChapters && !!metadata?.has_chapters} 
                                onChange={e => setEmbedChapters(e.target.checked)} 
                                disabled={!metadata?.has_chapters}
                              />
                              <span className="toggle-track" />
                            </label>
                          </div>
                        </div>
                      </div>

                      {/* 4. Save Location */}
                      <div className="workspace-group">
                        <span className="workspace-label">Save to</span>
                        <div className="save-location">
                          <FolderOpen size={15} className="save-location-icon" aria-hidden="true" />
                          <span className={`save-location-path ${!folder ? 'empty' : ''}`}>
                            {folder || 'Select a destination folder...'}
                          </span>
                          <button className="btn-browse" onClick={handleBrowse}>Browse</button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Download Button */}
                <div className="download-action-bar">
                  {!downloading ? (
                    <button className="btn-download" onClick={handleDownload} disabled={!urlInput.trim() || !folder.trim()}>
                      <Download size={17} /> Download Now
                    </button>
                  ) : (
                    <button className="btn-download downloading" disabled>
                      <RefreshCw size={15} className="spinner" /> Downloading...
                    </button>
                  )}
                  <button className="btn-cancel" onClick={handleCancel} disabled={!downloading}>Cancel</button>
                </div>
              </div>
            )}

            {/* Feature Cards */}
            {!metadata && !metadataLoading && (
              <div className="feature-cards">
                {[
                  { icon: <Zap size={16} />, title: 'Smart Detection', desc: 'Auto-detect video info and formats.' },
                  { icon: <EyeOff size={16} />, title: 'Smart Info Hiding', desc: 'Hides complex codecs (AVC1, VP09, Opus) with sleek badges & file sizes.' },
                  { icon: <ListMusic size={16} />, title: 'Playlist Support', desc: 'Download entire playlists at once.' },
                  { icon: <Download size={16} />, title: 'High Performance', desc: 'Multi-threaded parallel downloads.' },
                  { icon: <Shield size={16} />, title: 'Privacy First', desc: 'No data collection. Everything local.' },
                ].map((f, i) => (
                  <div key={i} className="feature-card">
                    <div className="feature-card-icon">{f.icon}</div>
                    <div className="feature-card-content">
                      <span className="feature-card-title">{f.title}</span>
                      <span className="feature-card-desc">{f.desc}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ──── HISTORY PAGE ──── */}
        {activePage === 'history' && (
          <div className="animate-fade-in" key="history">
            <div className="page-header">
              <div className="page-title-row">
                <div>
                  <h1 className="page-title">History</h1>
                  <p className="page-subtitle">Tracks and videos downloaded to this device</p>
                </div>
                {history.length > 0 && (
                  <div className="page-actions">
                    <button className="btn-clear-all" onClick={handleClearHistory}>
                      <Trash2 size={13} /> Clear All
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Search & Filters */}
            <div className="history-search-bar">
              <div className="history-search-input">
                <Search size={14} className="history-search-icon" />
                <input
                  type="text"
                  placeholder="Search downloads..."
                  value={historySearch}
                  onChange={(e) => setHistorySearch(e.target.value)}
                />
              </div>
              <div className="history-filters">
                {['all', 'audio', 'video'].map(f => (
                  <button key={f} className={`filter-chip ${historyFilter === f ? 'active' : ''}`} onClick={() => setHistoryFilter(f)}>
                    {f === 'all' ? 'All' : f === 'audio' ? 'Audio' : 'Video'}
                  </button>
                ))}
              </div>
            </div>

            {/* History List */}
            {filteredHistory.length === 0 ? (
              <div className="empty-state" key="history-empty">
                <div className="empty-state-icon"><HistoryIcon size={24} /></div>
                <h3 className="empty-state-title">No downloads yet</h3>
                <p className="empty-state-text">
                  {historySearch ? 'No results match your search.' : 'Your download history will appear here.'}
                </p>
              </div>
            ) : (
              <div className="history-list" key="history-list">
                {[...filteredHistory].reverse().map((item) => (
                  <div key={`${item.filePath}-${item.timestamp}`} className="history-card">
                    <div className="history-card-icon-fallback">
                      {item.format === 'audio' ? <Music size={16} /> : <Video size={16} />}
                    </div>
                    <div className="history-card-details">
                      <span className="history-card-title" title={item.title}>{item.title}</span>
                      <div className="history-card-meta">
                        <span>{item.format === 'audio' ? 'MP3' : 'MP4'}</span>
                        <span>•</span>
                        <span>{item.fileSize}</span>
                        <span>•</span>
                        <span>{item.timestamp}</span>
                      </div>
                    </div>
                    <div className="history-card-actions">
                      <button className="history-action-btn" onClick={() => handlePlayFile(item.filePath)}>
                        <Play size={12} style={{ fill: 'currentColor' }} /> Open
                      </button>
                      <button className="history-action-btn" onClick={() => handleOpenFolder(item.filePath)}>
                        <FolderOpen size={12} /> Folder
                      </button>
                      <button className="history-action-btn delete" onClick={() => handleDeleteHistory(item.filePath)}>
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ──── SETTINGS PAGE ──── */}
        {activePage === 'settings' && (
          <div className="animate-fade-in" key="settings">
            <div className="page-header">
              <h1 className="page-title">Settings</h1>
              <p className="page-subtitle">Configure application options and preferences</p>
            </div>

            <div className="settings-groups">
              {/* General */}
              <div className="settings-card">
                <div className="settings-card-header">General</div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <span className="settings-item-label">Default Folder</span>
                    <span className="settings-item-desc">Where downloaded files are saved by default.</span>
                  </div>
                  <button className="settings-btn" onClick={handleBrowse}>Change Folder</button>
                </div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <span className="settings-item-label">Show Notifications</span>
                    <span className="settings-item-desc">Display a notification when downloads complete.</span>
                  </div>
                  <label className="toggle" aria-label="Show notifications">
                    <input type="checkbox" checked={showNotification} onChange={e => setShowNotification(e.target.checked)} />
                    <span className="toggle-track" />
                  </label>
                </div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <span className="settings-item-label">Dark Mode</span>
                    <span className="settings-item-desc">Enable the modern pitch-black theme.</span>
                  </div>
                  <label className="toggle" aria-label="Toggle dark mode">
                    <input type="checkbox" checked={darkMode} onChange={e => setDarkMode(e.target.checked)} />
                    <span className="toggle-track" />
                  </label>
                </div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <span className="settings-item-label">UI Scaling</span>
                    <span className="settings-item-desc">Adjust the size of the user interface text and elements.</span>
                  </div>
                  <select
                    className="settings-select"
                    value={uiScale}
                    onChange={e => setUiScale(parseInt(e.target.value, 10))}
                    aria-label="UI Scaling"
                  >
                    <option value="100">100% (Default)</option>
                    <option value="125">125%</option>
                    <option value="150">150%</option>
                    <option value="175">175%</option>
                  </select>
                </div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <span className="settings-item-label">Bandwidth Limit</span>
                    <span className="settings-item-desc">Set the maximum download speed.</span>
                  </div>
                  <select
                    className="settings-select"
                    value={bandwidthLimit}
                    onChange={e => setBandwidthLimit(parseInt(e.target.value, 10))}
                    aria-label="Bandwidth Limit"
                  >
                    <option value="0">No Limit</option>
                    <option value="1">1 MB/s</option>
                    <option value="5">5 MB/s</option>
                    <option value="10">10 MB/s</option>
                    <option value="20">20 MB/s</option>
                  </select>
                </div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <span className="settings-item-label">Schedule Downloads</span>
                    <span className="settings-item-desc">Queue downloads to run automatically at a target time.</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    {scheduleEnabled && (
                      <input 
                        type="time" 
                        className="tag-input" 
                        style={{ width: 85, padding: '5px 8px', borderRadius: 'var(--radius-sm)' }}
                        value={scheduleTime} 
                        onChange={e => setScheduleTime(e.target.value)} 
                        aria-label="Schedule Time"
                      />
                    )}
                    <label className="toggle" aria-label="Toggle download scheduling">
                      <input type="checkbox" checked={scheduleEnabled} onChange={e => setScheduleEnabled(e.target.checked)} />
                      <span className="toggle-track" />
                    </label>
                  </div>
                </div>
              </div>

              {/* Downloads */}
              <div className="settings-card">
                <div className="settings-card-header">Downloads</div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <span className="settings-item-label">Embed Thumbnail</span>
                    <span className="settings-item-desc">Embed cover art into downloaded audio files.</span>
                  </div>
                  <label className="toggle" aria-label="Embed thumbnail in audio files">
                    <input type="checkbox" checked={embedThumbnail} onChange={e => setEmbedThumbnail(e.target.checked)} />
                    <span className="toggle-track" />
                  </label>
                </div>
              </div>

              {/* Dependencies & Updates */}
              <div className="settings-card dependencies-card">
                <div className="settings-card-header">Dependencies & System Health</div>
                
                {/* Health Summary Banner */}
                <div className={`health-summary ${dependencies.status === 'ready' ? 'healthy' : 'attention'}`}>
                  <span className="health-title">System Health Summary</span>
                  <div className="health-badge-row">
                    <span className="health-badge">
                      <span className="health-dot healthy" /> Bemudex
                    </span>
                    <span className="health-badge">
                      <span className={`health-dot ${dependencies.ytdlp.updateAvailable ? 'warning' : 'healthy'}`} /> yt-dlp
                    </span>
                    <span className="health-badge">
                      <span className={`health-dot ${dependencies.ffmpeg.installed ? 'healthy' : 'danger'}`} /> FFmpeg
                    </span>
                    <span className="health-badge">
                      <span className={`health-dot ${dependencies.folderWritable ? 'healthy' : 'danger'}`} /> Download Folder
                    </span>
                  </div>
                  <div className="health-status-msg">
                    {dependencies.status === 'ready' ? (
                      <span className="ready-text">✓ Ready to Download</span>
                    ) : !dependencies.ffmpeg.installed ? (
                      <span className="attention-text">⚠ Attention Required: FFmpeg Missing</span>
                    ) : !dependencies.folderWritable ? (
                      <span className="attention-text">⚠ Attention Required: Download folder isn't writable.</span>
                    ) : dependencies.ytdlp.updateAvailable ? (
                      <span className="attention-text">⚠ Attention Required: yt-dlp Update Available</span>
                    ) : (
                      <span className="attention-text">⚠ Attention Required: Configuration Issues</span>
                    )}
                  </div>
                </div>

                <div className="dependency-items-list">
                  {/* Bemudex */}
                  <div className="dependency-item">
                    <div className="dependency-info">
                      <span className="dependency-name">Bemudex Desktop App</span>
                      <div className="dependency-details">
                        <span>Version: <strong>{dependencies.bemudex.version}</strong></span>
                        <span>Build: <strong>{dependencies.bemudex.build}</strong></span>
                      </div>
                    </div>
                    <div className="dependency-actions">
                      <span className="status-label success">✓ Running latest version</span>
                    </div>
                  </div>

                  {/* yt-dlp */}
                  <div className="dependency-item">
                    <div className="dependency-info">
                      <span className="dependency-name">yt-dlp (Download Engine)</span>
                      <div className="dependency-details">
                        <span>Installed: <strong>{dependencies.ytdlp.version}</strong></span>
                        {dependencies.ytdlp.latestVersion && (
                          <span>Latest: <strong>{dependencies.ytdlp.latestVersion}</strong></span>
                        )}
                        {dependencies.lastCheckedStr && (
                          <span className="last-checked-label">Last Checked: {dependencies.lastCheckedStr}</span>
                        )}
                      </div>
                    </div>
                    <div className="dependency-actions">
                      {dependencies.ytdlp.status === 'checking' ? (
                        <span className="status-checking"><RefreshCw size={12} className="spinner" /> Checking...</span>
                      ) : dependencies.ytdlp.status === 'updating' ? (
                        <span className="status-updating"><RefreshCw size={12} className="spinner" /> Updating...</span>
                      ) : (
                        <>
                          {dependencies.ytdlp.updateAvailable ? (
                            <span className="status-label warning">Update Available</span>
                          ) : (
                            <span className="status-label success">✓ Up to date</span>
                          )}
                          <div className="btn-group-horizontal">
                            <button 
                              className="settings-btn secondary" 
                              onClick={() => handleCheckYtdlpUpdates()} 
                              disabled={dependencies.ytdlp.checking || dependencies.ytdlp.updating || downloading}
                            >
                              Check for Updates
                            </button>
                            {dependencies.ytdlp.updateAvailable && (
                              <button 
                                className="settings-btn primary" 
                                onClick={handleUpdateEngine} 
                                disabled={dependencies.ytdlp.updating || downloading}
                              >
                                Update Now
                              </button>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  </div>

                  {/* FFmpeg */}
                  <div className="dependency-item">
                    <div className="dependency-info">
                      <span className="dependency-name">FFmpeg (Media Converter)</span>
                      <div className="dependency-details">
                        {dependencies.ffmpeg.installed ? (
                          <span>Version: <strong>{dependencies.ffmpeg.version}</strong></span>
                        ) : (
                          <span className="text-danger">⚠ Not Installed</span>
                        )}
                      </div>
                      {!dependencies.ffmpeg.installed && (
                        <p className="dependency-explanation">
                          FFmpeg is required for merging high-quality video formats with audio tracks, and converting downloaded media to MP3, FLAC, or AAC formats.
                        </p>
                      )}
                    </div>
                    <div className="dependency-actions">
                      <div className="btn-group-horizontal">
                        <button 
                          className="settings-btn secondary" 
                          onClick={handleLocateFfmpeg} 
                          disabled={dependencies.ffmpeg.checking}
                        >
                          Locate FFmpeg
                        </button>
                        <button 
                          className="settings-btn secondary" 
                          onClick={handleInstallFfmpeg}
                        >
                          Install FFmpeg
                        </button>
                        <button 
                          className="settings-btn secondary" 
                          onClick={handleRetryFfmpegDetection} 
                          disabled={dependencies.ffmpeg.checking}
                        >
                          {dependencies.ffmpeg.checking ? (
                            <RefreshCw size={12} className="spinner" />
                          ) : 'Retry Detection'}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Options */}
                  <div className="dependency-item option-item">
                    <div className="dependency-info">
                      <span className="settings-item-label" style={{ fontWeight: 'normal' }}>Check for updates on launch</span>
                      <span className="settings-item-desc">Automatically check if download engine updates are available upon starting the application.</span>
                    </div>
                    <div className="dependency-actions">
                      <label className="toggle" aria-label="Auto check updates on startup">
                        <input type="checkbox" checked={autoUpdateCheck} onChange={e => setAutoUpdateCheck(e.target.checked)} />
                        <span className="toggle-track" />
                      </label>
                    </div>
                  </div>
                </div>
              </div>

              {/* Troubleshooting & Diagnostics */}
              <div className="settings-card">
                <div className="settings-card-header">Troubleshooting & Diagnostics</div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <span className="settings-item-label">Reset Dependency Configuration</span>
                    <span className="settings-item-desc">Remove custom paths and restore default autodetection settings.</span>
                  </div>
                  <button className="settings-btn warning-btn" onClick={handleResetDependencyConfig}>Reset Config</button>
                </div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <span className="settings-item-label">System Diagnostics Report</span>
                    <span className="settings-item-desc">View full diagnostic data to attach to bug reports and support requests.</span>
                  </div>
                  <button className="settings-btn" onClick={handleViewDiagnostics} disabled={loadingDiagnostics}>
                    {loadingDiagnostics ? <RefreshCw size={12} className="spinner" /> : 'View Diagnostics'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {showPanel && (
        <aside className="downloads-panel">
          <div className="panel-resize-handle" onMouseDown={handleResizeStart} />
          <div className="panel-header">
            <div className="panel-header-left">
              <span className="panel-title">Downloads</span>
              {activeCount > 0 && <span className="panel-count">{activeCount} Active</span>}
            </div>
            <div className="panel-actions">
              <button 
                className="panel-action-btn" 
                onClick={handleClearAll} 
                title="Clear all"
                disabled={
                  downloading 
                    ? (completed.length === 0 && !queue.some(i => i.status === 'failed'))
                    : (completed.length === 0 && queue.length === 0)
                }
              >
                <X size={15} />
              </button>
            </div>
          </div>

          <div className="panel-body">
            {/* Active Downloads */}
            {queue.map(item => (
              <DownloadCard
                key={item.id}
                item={item}
                onCancel={() => handleCancelItem(item)}
                onRetry={() => handleRetryDownload(item)}
              />
            ))}

            {/* Completed */}
            {completed.length > 0 && (
              <div className="completed-section">
                <div className="completed-header" onClick={() => setShowCompleted(!showCompleted)}>
                  <div className="completed-header-left">
                    {showCompleted ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                    <span>Completed</span>
                    <span className="completed-header-count">{completed.length}</span>
                  </div>
                </div>
                {showCompleted && (
                  <div className="completed-list">
                    {completed.map(item => (
                      <CompletedCard
                        key={item.id}
                        item={item}
                        onPlayFile={handlePlayFile}
                        onOpenFolder={handleOpenFolder}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Empty panel state */}
            {queue.length === 0 && completed.length === 0 && (
              <div className="panel-empty">
                <Download size={28} className="panel-empty-icon" />
                <span className="panel-empty-text">No active downloads</span>
              </div>
            )}
          </div>
        </aside>
      )}
    </div>
  );
}

export default App;
