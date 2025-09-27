import { useEffect, useRef, useState } from 'react';

type Props = {
  src: string;
  alt?: string;
  className?: string;
};

export default function LazyImg({ src, alt = '', className }: Props): JSX.Element {
  const imgRef = useRef<HTMLImageElement | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = imgRef.current;
    if (!node) return;
    if (typeof IntersectionObserver === 'undefined') {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setVisible(true);
        observer.disconnect();
      }
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return <img ref={imgRef} src={visible ? src : undefined} data-src={src} alt={alt} className={className} loading="lazy" />;
}
