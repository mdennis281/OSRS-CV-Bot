import type { Item } from '../../types/item';

/**
 * Renders a row of small FontAwesome-based property icons for an item.
 * Each icon has a tooltip explaining the property.
 */

interface Props {
  item: Pick<Item, 'members' | 'tradeable_on_ge' | 'stackable' | 'equipable' | 'noted' | 'noteable'>;
}

const PROPS: {
  key: keyof Props['item'];
  icon: string;
  label: string;
  activeColor: string;
}[] = [
  { key: 'members',        icon: 'fa-solid fa-star',           label: 'Members',   activeColor: 'var(--tag-members)' },
  { key: 'tradeable_on_ge', icon: 'fa-solid fa-coins',         label: 'Tradeable', activeColor: 'var(--tag-tradeable)' },
  { key: 'equipable',      icon: 'fa-solid fa-shield-halved',  label: 'Equipable', activeColor: 'var(--tag-equipable)' },
  { key: 'stackable',      icon: 'fa-solid fa-layer-group',    label: 'Stackable', activeColor: 'var(--tag-stackable)' },
  { key: 'noted',          icon: 'fa-solid fa-scroll',         label: 'Noted',     activeColor: 'var(--tag-noted)' },
  { key: 'noteable',       icon: 'fa-solid fa-file-lines',     label: 'Noteable',  activeColor: 'var(--tag-noteable)' },
];

export default function ItemPropIcons({ item }: Props) {
  return (
    <span className="item-prop-icons">
      {PROPS.map(({ key, icon, label, activeColor }) => {
        const active = !!item[key];
        return (
          <span
            key={key}
            className={`item-prop-icon ${active ? 'active' : 'inactive'}`}
            style={active ? { color: activeColor } : undefined}
            title={`${label}: ${active ? 'Yes' : 'No'}`}
          >
            <i className={icon} />
          </span>
        );
      })}
    </span>
  );
}
