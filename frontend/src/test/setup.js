import "@testing-library/jest-dom/vitest";

HTMLCanvasElement.prototype.getContext = () => ({
  clearRect() {},
  beginPath() {},
  moveTo() {},
  lineTo() {},
  closePath() {},
  fill() {},
  stroke() {},
  arc() {},
  fillRect() {},
  fillText() {},
  setLineDash() {},
});
