import type * as THREE from "three";

declare module "react" {
  namespace JSX {
    interface IntrinsicElements {
      meshLineGeometry: any;
      meshLineMaterial: {
        color?: string | number | THREE.Color;
        depthTest?: boolean;
        resolution?: [number, number] | THREE.Vector2;
        useMap?: boolean | number;
        map?: THREE.Texture | any;
        repeat?: [number, number] | THREE.Vector2;
        lineWidth?: number;
        attach?: string;
        opacity?: number;
        transparent?: boolean;
        [key: string]: any;
      };
    }
  }
}

export {};
