import { MorphIcon, type IconInput, type MorphIconProps } from 'morphicons/react'

type MorphGlyphProps = Omit<MorphIconProps, 'icon' | 'reducedMotion'> & {
  icon: IconInput
}

export function MorphGlyph({ icon, size = 16, strokeWidth = 1.8, ...props }: MorphGlyphProps) {
  return (
    <MorphIcon
      icon={icon}
      size={size}
      strokeWidth={strokeWidth}
      spring="snappy"
      reducedMotion="user"
      {...props}
    />
  )
}
