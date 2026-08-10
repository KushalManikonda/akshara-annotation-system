import { useState, useCallback } from 'react';

export function useUndoRedo<T>(initialState: T) {
  const [state, setState] = useState<T>(initialState);
  const [past, setPast] = useState<T[]>([]);
  const [future, setFuture] = useState<T[]>([]);

  const set = useCallback((newState: T | ((curr: T) => T)) => {
    setState((currentState) => {
      const resolvedState = typeof newState === 'function' ? (newState as Function)(currentState) : newState;
      if (resolvedState === currentState) return currentState;
      
      setPast((p) => [...p, currentState]);
      setFuture([]);
      return resolvedState;
    });
  }, []);

  const undo = useCallback(() => {
    setState((currentState) => {
      if (past.length === 0) return currentState;
      const previous = past[past.length - 1];
      const newPast = past.slice(0, past.length - 1);
      
      setPast(newPast);
      setFuture((f) => [currentState, ...f]);
      return previous;
    });
  }, [past]);

  const redo = useCallback(() => {
    setState((currentState) => {
      if (future.length === 0) return currentState;
      const next = future[0];
      const newFuture = future.slice(1);
      
      setPast((p) => [...p, currentState]);
      setFuture(newFuture);
      return next;
    });
  }, [future]);

  const reset = useCallback((newState: T) => {
    setState(newState);
    setPast([]);
    setFuture([]);
  }, []);

  return { state, set, undo, redo, reset, canUndo: past.length > 0, canRedo: future.length > 0 };
}
