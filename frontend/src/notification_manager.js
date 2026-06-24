export class NotificationManager {
  constructor(setToasts, toastIdRef) {
    this.setToasts = setToasts;
    this.toastIdRef = toastIdRef;
  }

  show(message, type = 'info', duration = 4000) {
    if (!message) return;
    this.setToasts(prev => {
      // Deduplicate active toasts
      if (prev.some(t => t.message === message)) return prev;
      
      const id = ++this.toastIdRef.current;
      setTimeout(() => {
        this.setToasts(current => current.filter(t => t.id !== id));
      }, duration);
      
      return [...prev, { id, message, type }];
    });
  }

  success(msg) { this.show(msg, 'success', 4000); }
  info(msg) { this.show(msg, 'info', 4000); }
  warning(msg) { this.show(msg, 'warning', 5000); }
  error(msg) { this.show(msg, 'error', 6000); }
}
