import {useEffect} from 'react';

export function useTitle(title: string) {
  useEffect(() => {
    document.title = `${title} · AI Room Club`;
  }, [title]);
}
