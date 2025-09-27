import { describe, expect, it } from 'vitest';

import BoardingCheckIn from '../BoardingCheckIn';
import BoardingCheckOut from '../BoardingCheckOut';
import DaycareCheckIn from '../DaycareCheckIn';
import DaycareCheckOut from '../DaycareCheckOut';
import GroomingLane from '../GroomingLane';
import Home from '../Home';
import QuickPrint from '../QuickPrint';
import Shell from '../Shell';

const components = [
  BoardingCheckIn,
  BoardingCheckOut,
  DaycareCheckIn,
  DaycareCheckOut,
  GroomingLane,
  Home,
  QuickPrint,
  Shell,
];

describe('kiosk suite', () => {
  it('exports kiosk components as functions', () => {
    for (const component of components) {
      expect(typeof component).toBe('function');
    }
  });
});
